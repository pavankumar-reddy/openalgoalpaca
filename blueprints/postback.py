"""
Broker postback (webhook) receivers for real-time order updates.
"""

import hashlib
import os

from flask import Blueprint, jsonify, request

from database.auth_db import Auth
from utils.event_bus import bus
from utils.logging import get_logger
from websocket_proxy.order_adapter import to_openalgo_symbol

logger = get_logger(__name__)

postback_bp = Blueprint("postback_bp", __name__, url_prefix="/postback")

SUPPORTED_BROKERS: set[str] = set()

_NORMALIZERS: dict = {}


def _get_active_session() -> Auth | None:
    """Return the instance's active (non-revoked) broker session, if any."""
    try:
        return Auth.query.filter_by(is_revoked=False).first()
    except Exception:
        logger.exception("Postback: failed to read active broker session")
        return None


def _publish(user_id: str, broker: str, fields: dict) -> None:
    from events import OrderUpdateEvent

    fields.setdefault("mode", "live")
    fields.setdefault("broker", broker)
    fields.setdefault("api_type", f"{broker}.postback")
    fields.setdefault("request_data", {"user_id": user_id})
    bus.publish(OrderUpdateEvent(**fields))


@postback_bp.route("/<broker>", methods=["POST"])
def broker_postback(broker: str):
    broker = broker.lower()
    if broker not in SUPPORTED_BROKERS:
        return jsonify({"status": "error", "message": f"Unsupported broker: {broker}"}), 404

    session_obj = _get_active_session()
    if session_obj is None or (session_obj.broker or "").lower() != broker:
        logger.warning(f"Postback for '{broker}' rejected — no matching active broker session")
        return jsonify({"status": "error", "message": "No matching broker session"}), 403

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        data = request.form.to_dict() or None
    if not isinstance(data, dict) or not data:
        return jsonify({"status": "error", "message": "Invalid payload"}), 400

    try:
        fields = _NORMALIZERS[broker](data)
    except Exception:
        logger.exception(f"Postback normalization failed for {broker}")
        return jsonify({"status": "error", "message": "Payload normalization failed"}), 400

    if fields:
        _publish(session_obj.name, broker, fields)
        logger.info(
            f"Postback order update ({broker}): orderid={fields.get('orderid')} "
            f"status={fields.get('order_status')}"
        )

    return jsonify({"status": "success"}), 200


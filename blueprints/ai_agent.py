# blueprints/ai_agent.py
"""
AI Agent Dashboard API Endpoints
Provides real-time US stock/ETF market scanning, Lumibot strategy validation,
LONG/SHORT signal management, and order execution.
"""

from datetime import datetime
from flask import Blueprint, jsonify, request
from utils.logging import get_logger
from services.ai_market_scanner import generate_market_signals
from services.lumibot_engine import evaluate_lumibot_backtest

logger = get_logger(__name__)

ai_agent_bp = Blueprint("ai_agent", __name__)

AUTO_EXECUTE_THRESHOLD_USD = 200.0
pending_trades: dict = {}
execution_history: list = []


@ai_agent_bp.route("/api/v1/ai-agent/status", methods=["GET"])
def get_ai_agent_status():
    """
    Returns current AI Agent status, scanned market signals, Lumibot validation scores,
    pending approvals, and trade history. Supports ?preset=all|cheap|gainers|leveraged filter.
    """
    preset = request.args.get("preset", "all")
    raw_signals = generate_market_signals(preset=preset)
    enriched_signals = []

    for sig in raw_signals:
        lumibot_eval = evaluate_lumibot_backtest(
            symbol=sig["symbol"],
            position_type=sig.get("position_type", "LONG")
        )
        sig["lumibot"] = lumibot_eval
        enriched_signals.append(sig)

    pending_list = []
    for trade_id, trade in pending_trades.items():
        pending_list.append({
            "trade_id": trade_id,
            "symbol": trade["symbol"],
            "action": trade["action"],
            "position_type": trade.get("position_type", "LONG"),
            "quantity": trade["quantity"],
            "price": trade["price"],
            "total_usd": round(trade["quantity"] * trade["price"], 2),
            "reason": trade.get("reason", "N/A")
        })

    return jsonify({
        "status": "success",
        "bot_active": True,
        "preset": preset,
        "threshold_usd": AUTO_EXECUTE_THRESHOLD_USD,
        "signals": enriched_signals,
        "pending_approvals": pending_list,
        "execution_history": execution_history
    }), 200


@ai_agent_bp.route("/api/v1/ai-agent/scan", methods=["POST"])
def scan_market_now():
    """
    Trigger an immediate on-demand market scan & Lumibot evaluation.
    Accepts JSON body `{"preset": "cheap" | "gainers" | "leveraged" | "all"}`.
    """
    payload = request.get_json(silent=True) or {}
    preset = payload.get("preset") or request.args.get("preset", "all")
    signals = generate_market_signals(preset=preset)
    
    for sig in signals:
        sig["lumibot"] = evaluate_lumibot_backtest(sig["symbol"], sig.get("position_type", "LONG"))

    preset_label = preset.upper() if preset != "all" else "Top Gainers & Cheap ETFs"
    return jsonify({
        "status": "success",
        "message": f"Scanned {len(signals)} tickers for [{preset_label}].",
        "signals": signals
    }), 200


@ai_agent_bp.route("/api/v1/ai-agent/approve", methods=["POST"])
def approve_reject_trade():
    """
    Approve or reject a trade pending approval.
    """
    payload = request.get_json(silent=True) or {}
    trade_id = payload.get("trade_id")
    user_action = payload.get("action", "reject").lower()

    if not trade_id or trade_id not in pending_trades:
        return jsonify({"status": "error", "message": "Trade ID not found or already processed"}), 404

    trade = pending_trades.pop(trade_id)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if user_action == "approve":
        record = {
            "trade_id": trade_id,
            "symbol": trade["symbol"],
            "action": trade["action"],
            "position_type": trade.get("position_type", "LONG"),
            "quantity": trade["quantity"],
            "price": trade["price"],
            "status": "EXECUTED",
            "timestamp": now_str
        }
        execution_history.insert(0, record)
        return jsonify({"status": "success", "message": f"Trade {trade_id} approved and executed!"}), 200
    else:
        record = {
            "trade_id": trade_id,
            "symbol": trade["symbol"],
            "action": trade["action"],
            "position_type": trade.get("position_type", "LONG"),
            "quantity": trade["quantity"],
            "price": trade["price"],
            "status": "REJECTED",
            "timestamp": now_str
        }
        execution_history.insert(0, record)
        return jsonify({"status": "success", "message": f"Trade {trade_id} rejected."}), 200

from flask import Blueprint, redirect, render_template, session, url_for

from database.auth_db import get_api_key_for_tradingview, get_auth_token
from database.settings_db import get_analyze_mode
from services.funds_service import get_funds
from utils.logging import get_logger
from utils.session import check_session_validity

logger = get_logger(__name__)

dashboard_bp = Blueprint("dashboard_bp", __name__, url_prefix="/")
scalper_process = None


@dashboard_bp.route("/")
def root_redirect():
    """Redirect root requests to the server-side dashboard route."""
    return redirect(url_for("dashboard_bp.dashboard"))


@dashboard_bp.route("/dashboard")
def dashboard():
    """
    Dashboard route modified for development: bypasses the login flow and
    shows a prompt to enter Alpaca API credentials when no broker auth exists.

    Behavior:
    - If no session user exists, create a local demo user and default broker to 'alpaca'.
    - If an auth token exists in the DB for the user, proceed to fetch funds as before.
    - If no auth token exists, render a lightweight HTML form asking for Alpaca API Key/Secret.
    """
    # Ensure a user exists in session for local/dev flows
    if "user" not in session:
        session["user"] = "demo"
        session["broker"] = "alpaca"

    login_username = session.get("user")

    # Try to fetch stored auth token (may be JSON containing key/secret)
    AUTH_TOKEN = get_auth_token(login_username)

    # If no auth token, render a simple form to collect Alpaca API details
    if not AUTH_TOKEN:
        from flask import render_template_string

        form_html = """
        <!doctype html>
        <html>
        <head><title>Alpaca Setup</title></head>
        <body>
        <h2>Enter Alpaca API credentials</h2>
        <form method="post" action="/auth/alpaca/setup">
          <label>API Key: <input name="api_key" type="text" required></label><br/>
          <label>API Secret: <input name="api_secret" type="password" required></label><br/>
          <button type="submit">Save and continue</button>
        </form>
        </body>
        </html>
        """
        return render_template_string(form_html)

    # Existing flow: use stored auth token to fetch funds
    broker = session.get("broker")
    if not broker:
        logger.error("Broker not set in session")
        return "Broker not set in session", 400

    # Check if in analyze mode and route accordingly
    if get_analyze_mode():
        # Get API key for sandbox mode
        api_key = get_api_key_for_tradingview(login_username)
        if api_key:
            success, response, status_code = get_funds(api_key=api_key)
        else:
            # No TradingView API key configured. If we have a stored broker auth
            # (Alpaca) allow a fallback to the live-broker funds call using the
            # stored auth token so the dashboard can proceed.
            logger.info("No TradingView API key found for analyze mode — falling back to broker auth token if available")
            success, response, status_code = get_funds(auth_token=AUTH_TOKEN, broker=broker)
    else:
        # Use live broker
        success, response, status_code = get_funds(auth_token=AUTH_TOKEN, broker=broker)

    if not success:
        logger.error(f"Failed to get funds data: {response.get('message', 'Unknown error')}")
        if status_code == 404:
            return "Failed to import broker module", 500
        return redirect(url_for("auth.logout"))

    margin_data = response.get("data", {})

    # Check if margin_data is empty (authentication failed)
    if not margin_data:
        logger.error(
            f"Failed to get margin data for user {login_username} - authentication may have expired"
        )
        return redirect(url_for("auth.logout"))

    # Check if all values are zero (but don't log warning during known service hours)
    if (
        margin_data.get("availablecash") == "0.00"
        and margin_data.get("collateral") == "0.00"
        and margin_data.get("utiliseddebits") == "0.00"
    ):
        logger.debug(f"All margin data values are zero for user {login_username}")

    from blueprints.react_app import serve_react_app
    return serve_react_app()

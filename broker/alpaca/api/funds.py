# broker/alpaca/api/funds.py
import os
import logging
from decimal import Decimal
from utils.httpx_client import get_httpx_client

logger = logging.getLogger(__name__)

def get_margin_data(auth_token):
    """
    Fetch margin and account balance details from Alpaca API.
    """
    api_key = None
    api_secret = None
    if auth_token:
        try:
            import json
            creds = json.loads(auth_token)
            api_key = creds.get("api_key")
            api_secret = creds.get("api_secret")
        except Exception:
            pass

    if not api_key:
        api_key = os.getenv("BROKER_API_KEY")
    if not api_secret:
        api_secret = os.getenv("BROKER_API_SECRET")

    paper_mode = os.getenv("ALPACA_PAPER_MODE", "True").upper() == "TRUE"
    default_url = "https://paper-api.alpaca.markets" if paper_mode else "https://api.alpaca.markets"
    base_url = os.getenv("ALPACA_BASE_URL", default_url)
    
    if not api_key or not api_secret:
        logger.error("Alpaca funds query failed: api_key or api_secret not set.")
        return {}

    client = get_httpx_client()
    headers = {
        "APCA-API-KEY-ID": api_key,
        "APCA-API-SECRET-KEY": api_secret,
        "Content-Type": "application/json"
    }

    try:
        # 1. Fetch account details
        response = client.get(f"{base_url}/v2/account", headers=headers)
        response.raise_for_status()
        account_data = response.json()

        # 2. Fetch positions to calculate unrealized P&L
        total_unrealised = Decimal("0.00")
        try:
            pos_resp = client.get(f"{base_url}/v2/positions", headers=headers)
            if pos_resp.status_code == 200:
                positions = pos_resp.json()
                for pos in positions:
                    unrealized_pl = pos.get("unrealized_pl", "0")
                    total_unrealised += Decimal(str(unrealized_pl))
        except Exception as e:
            logger.warning(f"Alpaca funds: unable to fetch positions for unrealized P&L: {e}")

        cash = Decimal(account_data.get("cash", "0.00"))
        portfolio_value = Decimal(account_data.get("portfolio_value", "0.00"))
        equity = Decimal(account_data.get("equity", "0.00"))
        long_market_value = Decimal(account_data.get("long_market_value", "0.00"))

        processed_margin_data = {
            "availablecash": f"{cash:.2f}",
            "collateral": f"{portfolio_value:.2f}",
            "m2munrealized": f"{total_unrealised:.2f}",
            "m2mrealized": "0.00",
            "utiliseddebits": f"{long_market_value:.2f}",
        }
        return processed_margin_data

    except Exception as e:
        logger.exception(f"Error fetching Alpaca margin data: {e}")
        return {}

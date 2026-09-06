# broker/ibkr/api/funds.py
import os
import logging
from decimal import Decimal
from utils.httpx_client import get_httpx_client

logger = logging.getLogger(__name__)

def get_margin_data(auth_token):
    """
    Fetch margin and account balances from IBKR Client Portal API.
    """
    base_url = os.getenv("IBKR_BASE_URL", "https://localhost:5000/v1/portal")
    client = get_httpx_client()

    try:
        # 1. Fetch accounts to get the active account ID
        acc_resp = client.get(f"{base_url}/portfolio/accounts", verify=False)
        acc_resp.raise_for_status()
        accounts = acc_resp.json()
        
        if not accounts:
            logger.error("IBKR: No accounts found.")
            return {}

        account_id = accounts[0].get("id")

        # 2. Fetch ledger details
        ledger_resp = client.get(f"{base_url}/portfolio/{account_id}/ledger", verify=False)
        ledger_resp.raise_for_status()
        ledger = ledger_resp.json()

        # Extract values
        usd_ledger = ledger.get("BASE", {}) or ledger.get("USD", {})
        
        cash = Decimal(str(usd_ledger.get("cashbalance", "0.00")))
        net_liquidation = Decimal(str(usd_ledger.get("netliquidation", "0.00")))
        unrealized_pnl = Decimal(str(usd_ledger.get("unrealizedpnl", "0.00")))
        realized_pnl = Decimal(str(usd_ledger.get("realizedpnl", "0.00")))
        initial_margin = Decimal(str(usd_ledger.get("initialmargin", "0.00")))

        processed_margin_data = {
            "availablecash": f"{cash:.2f}",
            "collateral": f"{net_liquidation:.2f}",
            "m2munrealized": f"{unrealized_pnl:.2f}",
            "m2mrealized": f"{realized_pnl:.2f}",
            "utiliseddebits": f"{initial_margin:.2f}",
        }
        return processed_margin_data

    except Exception as e:
        logger.exception(f"Error fetching IBKR margin data: {e}")
        return {}

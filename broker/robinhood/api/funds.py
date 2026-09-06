# broker/robinhood/api/funds.py
import logging
from decimal import Decimal
from utils.httpx_client import get_httpx_client

logger = logging.getLogger(__name__)

def get_margin_data(auth_token):
    """
    Fetch margin and cash details from Robinhood.
    """
    client = get_httpx_client()
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0"
    }

    try:
        # Check if robin_stocks is installed
        try:
            import robin_stocks.robinhood as r
            # robin_stocks relies on its internal global state/session, so we assume login happened
            profile = r.load_portfolio_profile()
            cash = Decimal(str(profile.get("withdrawable_amount", "0.00")))
            equity = Decimal(str(profile.get("equity", "0.00")))
            market_value = Decimal(str(profile.get("market_value", "0.00")))
            
            processed_margin_data = {
                "availablecash": f"{cash:.2f}",
                "collateral": f"{equity:.2f}",
                "m2munrealized": "0.00",
                "m2mrealized": "0.00",
                "utiliseddebits": f"{market_value:.2f}",
            }
            return processed_margin_data
        except (ImportError, Exception):
            pass

        # REST API Fallback
        acc_resp = client.get("https://api.robinhood.com/accounts/", headers=headers)
        acc_resp.raise_for_status()
        acc_data = acc_resp.json()
        
        if not acc_data.get("results"):
            return {}

        account = acc_data["results"][0]
        buying_power = Decimal(str(account.get("buying_power", "0.00")))
        
        # Portfolio value
        portfolio_url = account.get("portfolio", "")
        if portfolio_url:
            port_resp = client.get(portfolio_url, headers=headers)
            port_data = port_resp.json()
            market_value = Decimal(str(port_data.get("market_value", "0.00")))
            equity = Decimal(str(port_data.get("equity", "0.00")))
        else:
            market_value = Decimal("0.00")
            equity = buying_power

        processed_margin_data = {
            "availablecash": f"{buying_power:.2f}",
            "collateral": f"{equity:.2f}",
            "m2munrealized": "0.00",
            "m2mrealized": "0.00",
            "utiliseddebits": f"{market_value:.2f}",
        }
        return processed_margin_data

    except Exception as e:
        logger.exception(f"Error fetching Robinhood margin data: {e}")
        return {}

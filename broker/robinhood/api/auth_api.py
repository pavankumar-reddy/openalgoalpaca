# broker/robinhood/api/auth_api.py
import os
import logging
from utils.httpx_client import get_httpx_client

logger = logging.getLogger(__name__)

def authenticate_broker(*args, **kwargs):
    """
    Authenticate Robinhood.
    If username/password are provided, tries login using REST.
    Otherwise, reads credentials from environment variables.
    """
    try:
        username = os.getenv("BROKER_API_KEY")  # mapping username to BROKER_API_KEY
        password = os.getenv("BROKER_API_SECRET")  # mapping password to BROKER_API_SECRET
        
        if not username or not password:
            logger.error("Robinhood login failed: BROKER_API_KEY (username) or BROKER_API_SECRET (password) not set.")
            return None, "BROKER_API_KEY (username) or BROKER_API_SECRET (password) not set."

        # Check if robin_stocks is installed
        try:
            import robin_stocks.robinhood as r
            logger.info("Robinhood: Using robin_stocks library for login.")
            login_data = r.login(username, password, expires_in=86400, by_sms=True)
            token = login_data.get("access_token")
            if token:
                return token, None
        except ImportError:
            logger.info("Robinhood: robin_stocks not installed. Fallback to direct HTTP request.")

        # HTTP REST Fallback
        client = get_httpx_client()
        payload = {
            "client_id": "c827e2a6-91cd-4b11-a50e-9d8b113b2c40",  # Robinhood standard client_id
            "grant_type": "password",
            "username": username,
            "password": password,
            "scope": "internal"
        }
        
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0"
        }

        response = client.post("https://api.robinhood.com/oauth/authorizations/", headers=headers, json=payload)
        res_data = response.json()
        
        if response.status_code == 200:
            token = res_data.get("access_token")
            return token, None
        else:
            return None, res_data.get("detail", "Authentication failed")

    except Exception as e:
        logger.exception("Error authenticating Robinhood")
        return None, str(e)

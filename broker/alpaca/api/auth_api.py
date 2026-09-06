# broker/alpaca/api/auth_api.py
import os
import logging
import json
from utils.httpx_client import get_httpx_client

logger = logging.getLogger(__name__)

def authenticate_broker(api_key=None, api_secret=None, *args, **kwargs):
    """
    Authenticate Alpaca broker.
    Tests the provided API keys against the Alpaca account endpoint.
    If valid, returns the credentials JSON string as the auth token.
    """
    if not api_key or not api_secret:
        return None, "API Key ID and Secret Key are required."
        
    paper_mode = os.getenv("ALPACA_PAPER_MODE", "True").upper() == "TRUE"
    default_url = "https://paper-api.alpaca.markets" if paper_mode else "https://api.alpaca.markets"
    base_url = os.getenv("ALPACA_BASE_URL", default_url)
    
    client = get_httpx_client()
    headers = {
        "APCA-API-KEY-ID": api_key,
        "APCA-API-SECRET-KEY": api_secret,
        "Content-Type": "application/json"
    }
    
    try:
        response = client.get(f"{base_url}/v2/account", headers=headers)
        if response.status_code == 200:
            logger.info("Alpaca authentication successful.")
            token_payload = json.dumps({"api_key": api_key, "api_secret": api_secret})
            return token_payload, None
        else:
            err_msg = "Invalid API Key ID or Secret Key."
            try:
                err_msg = response.json().get("message", err_msg)
            except Exception:
                pass
            logger.error(f"Alpaca authentication failed: {err_msg}")
            return None, err_msg
    except Exception as e:
        logger.exception("Error during Alpaca authentication")
        return None, str(e)

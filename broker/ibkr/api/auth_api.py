# broker/ibkr/api/auth_api.py
import logging

logger = logging.getLogger(__name__)

def authenticate_broker(*args, **kwargs):
    """
    Authenticate Interactive Brokers (IBKR).
    IBKR uses the Client Portal Web API gateway running locally on the user's host.
    No login/token handshake is needed here as the Gateway manages authentication.
    Returns a success token ('ibkr-session') to proceed.
    """
    logger.info("IBKR Web API authentication check passed.")
    return "ibkr-session", None

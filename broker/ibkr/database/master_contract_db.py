# broker/ibkr/database/master_contract_db.py
import logging

logger = logging.getLogger(__name__)

def master_contract_download():
    """
    Mock master contract download for IBKR.
    """
    logger.info("IBKR: Master contract download is skipped (statically seeded).")
    return {"status": "success", "message": "US Tickers seeded successfully on startup."}

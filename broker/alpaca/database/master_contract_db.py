# broker/alpaca/database/master_contract_db.py
import logging

logger = logging.getLogger(__name__)

def master_contract_download():
    """
    Mock master contract download for Alpaca.
    Since Alpaca uses the statically seeded US tickers database,
    no download is necessary. Returns success directly.
    """
    logger.info("Alpaca: Master contract download is skipped (statically seeded).")
    return {"status": "success", "message": "US Tickers seeded successfully on startup."}

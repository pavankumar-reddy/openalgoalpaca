from datetime import datetime, timedelta

import pytz

from utils.logging import get_logger

# Initialize logger
logger = get_logger(__name__)


def get_session_expiry_time():
    now_utc = datetime.now(pytz.timezone("UTC"))
    now_est = now_utc.astimezone(pytz.timezone("America/New_York"))
    logger.debug(f"Current EST time: {now_est}")
    target_time_est = now_est.replace(hour=3, minute=0, second=0, microsecond=0)
    if now_est > target_time_est:
        target_time_est += timedelta(days=1)
    remaining_time = target_time_est - now_est
    return remaining_time

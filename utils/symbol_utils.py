# utils/symbol_utils.py
"""
Shared symbol classification helpers used across the sandbox and other modules.
"""

from utils.constants import CRYPTO_EXCHANGES, FNO_EXCHANGES
from database.token_db_enhanced import fno_search_symbols
from utils.constants import INSTRUMENT_PERPFUT


def get_underlying_quote_symbol(base_symbol: str, exchange: str) -> str:
    """Return the quote symbol for an underlying, appending the crypto quote currency if needed.

    For crypto exchanges: canonical perpetual (e.g. BTCUSD.P)
    For all other exchanges: base_symbol unchanged
    """
    if exchange.upper() in CRYPTO_EXCHANGES:
        _perp = fno_search_symbols(
            underlying=base_symbol.upper(),
            exchange=exchange,
            instrumenttype=INSTRUMENT_PERPFUT,
            limit=1,
        )
        if _perp:
            return _perp[0]["symbol"]
        return f"{base_symbol.upper()}USD.P"
    return base_symbol


import re


def is_option(symbol: str, exchange: str) -> bool:
    """Check if symbol is an option based on exchange and canonical symbol suffix."""
    if not symbol:
        return False
    # Matches OSI format (C/P followed by 8 digits at the end) or legacy CE/PE
    if re.search(r"[CP]\d{8}$", symbol) or symbol.endswith("CE") or symbol.endswith("PE"):
        return True
    return False


def is_future(symbol: str, exchange: str) -> bool:
    """Check if symbol is a future (or perpetual) based on exchange and canonical symbol suffix."""
    if not symbol:
        return False
    # Both are non-options so: is_future ≡ not is_option for the CRYPTO exchange.
    if exchange in CRYPTO_EXCHANGES:
        return not is_option(symbol, exchange)
    return symbol.endswith("FUT")

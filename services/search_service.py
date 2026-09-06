from typing import Any, Dict, List, Tuple

from database.auth_db import verify_api_key
from database.qty_freeze_db import get_freeze_qty_for_option
from database.token_db_enhanced import get_cache
from utils.logging import get_logger

logger = get_logger(__name__)


def dynamic_us_symbol_lookup(symbol: str) -> bool:
    """
    Look up symbol from active broker API dynamically, insert into DB, and reload cache.
    Returns True if symbol was found and added.
    """
    symbol = symbol.strip().upper()
    if not symbol:
        return False

    from database.auth_db import Auth
    
    # 1. Try Alpaca
    auth_obj = Auth.query.filter_by(broker="alpaca", is_revoked=False).first()
    if auth_obj:
        try:
            from database.auth_db import decrypt_token
            import json
            import os
            from utils.httpx_client import get_httpx_client
            from database.symbol import SymToken, db_session
            
            credentials = json.loads(decrypt_token(auth_obj.auth))
            api_key = credentials.get("api_key")
            api_secret = credentials.get("api_secret")
            if not api_key or not api_secret:
                return False

            paper_mode = os.getenv("ALPACA_PAPER_MODE", "True").upper() == "TRUE"
            default_url = "https://paper-api.alpaca.markets" if paper_mode else "https://api.alpaca.markets"
            base_url = os.getenv("ALPACA_BASE_URL", default_url)

            headers = {
                "APCA-API-KEY-ID": api_key,
                "APCA-API-SECRET-KEY": api_secret,
                "Content-Type": "application/json"
            }

            client = get_httpx_client()
            response = client.get(f"{base_url}/v2/assets/{symbol}", headers=headers)
            if response.status_code == 200:
                asset = response.json()
                if asset.get("tradable"):
                    session = db_session
                    raw_ex = (asset.get("exchange") or "NASDAQ").upper()
                    if raw_ex in ["BATS", "ARCA", "NYSE_ARCA", "AMEX"]:
                        std_exchange = "AMEX" if raw_ex == "AMEX" else "NASDAQ"
                    elif raw_ex in ["NASDAQ", "NYSE", "OTCQX"]:
                        std_exchange = raw_ex
                    else:
                        std_exchange = "NASDAQ"

                    if not existing:
                        new_token = SymToken(
                            symbol=symbol,
                            brsymbol=symbol,
                            name=asset.get("name", f"{symbol} Stock"),
                            exchange=std_exchange,
                            brexchange=std_exchange,
                            token=symbol,
                            lotsize=1,
                            instrumenttype="EQUITY",
                            tick_size=0.01,
                            contract_value=1.0
                        )
                        session.add(new_token)
                        session.commit()
                        
                        # Reload cache
                        cache = get_cache()
                        cache.load_all_symbols("alpaca")
                        logger.info(f"US Ticker Seeder: Dynamically seeded {symbol} from Alpaca API.")
                        return True
        except Exception as e:
            logger.error(f"Error dynamically loading symbol {symbol} from Alpaca: {e}")

    # 2. Try Robinhood
    auth_obj_rh = Auth.query.filter_by(broker="robinhood", is_revoked=False).first()
    if auth_obj_rh:
        try:
            from utils.httpx_client import get_httpx_client
            from database.symbol import SymToken, db_session
            
            client = get_httpx_client()
            response = client.get(f"https://api.robinhood.com/quotes/{symbol}/")
            if response.status_code == 200:
                quote = response.json()
                session = db_session
                existing = session.query(SymToken).filter_by(symbol=symbol).first()
                if not existing:
                    new_token = SymToken(
                        symbol=symbol,
                        brsymbol=symbol,
                        name=quote.get("instrument", f"{symbol} Stock"),
                        exchange="NASDAQ",
                        brexchange="NASDAQ",
                        token=symbol,
                        lotsize=1,
                        instrumenttype="EQUITY",
                        tick_size=0.01,
                        contract_value=1.0
                    )
                    session.add(new_token)
                    session.commit()
                    
                    # Reload cache
                    cache = get_cache()
                    cache.load_all_symbols("robinhood")
                    logger.info(f"US Ticker Seeder: Dynamically seeded {symbol} from Robinhood API.")
                    return True
        except Exception as e:
            logger.error(f"Error dynamically loading symbol {symbol} from Robinhood: {e}")

    # 3. Try IBKR
    auth_obj_ib = Auth.query.filter_by(broker="ibkr", is_revoked=False).first()
    if auth_obj_ib:
        try:
            from utils.httpx_client import get_httpx_client
            from database.symbol import SymToken, db_session
            from broker.ibkr.api.data import get_base_url, get_conid_by_symbol
            
            client = get_httpx_client()
            base_url = get_base_url()
            conid = get_conid_by_symbol(client, base_url, symbol)
            if conid:
                session = db_session
                existing = session.query(SymToken).filter_by(symbol=symbol).first()
                if not existing:
                    new_token = SymToken(
                        symbol=symbol,
                        brsymbol=symbol,
                        name=f"{symbol} Stock",
                        exchange="NASDAQ",
                        brexchange="NASDAQ",
                        token=symbol,
                        lotsize=1,
                        instrumenttype="EQUITY",
                        tick_size=0.01,
                        contract_value=1.0
                    )
                    session.add(new_token)
                    session.commit()
                    
                    # Reload cache
                    cache = get_cache()
                    cache.load_all_symbols("ibkr")
                    logger.info(f"US Ticker Seeder: Dynamically seeded {symbol} from IBKR API.")
                    return True
        except Exception as e:
            logger.error(f"Error dynamically loading symbol {symbol} from IBKR: {e}")

    return False


def search_symbols(
    query: str, exchange: str = None, api_key: str = None
) -> tuple[bool, dict[str, Any], int]:
    """
    Search for symbols using in-memory cache for fast performance.
    Falls back to database if cache is not available.

    Args:
        query: Search query/symbol name
        exchange: Optional exchange filter (NSE, BSE, etc.)
        api_key: API key for authentication

    Returns:
        Tuple of (success, response_data, status_code)
    """
    try:
        # Validate API key if provided
        if api_key:
            user_id = verify_api_key(api_key)
            if not user_id:
                logger.warning("Invalid API key provided for search")
                return False, {"status": "error", "message": "Invalid openalgo apikey"}, 403

        # Validate input
        if not query or not query.strip():
            logger.warning("Empty search query provided")
            return (
                False,
                {"status": "error", "message": "Query parameter is required and cannot be empty"},
                400,
            )

        query = query.strip()
        logger.info(f"Searching symbols for query: {query}, exchange: {exchange}")

        # Try cache-based search first
        cache = get_cache()
        if cache.cache_loaded and cache.is_cache_valid():
            results = cache.search_symbols(query, exchange, limit=500)

            if not results and len(query) >= 1 and len(query) <= 5 and query.isalpha():
                if dynamic_us_symbol_lookup(query):
                    results = cache.search_symbols(query, exchange, limit=500)

            if not results:
                logger.info(f"No results found for query: {query}")
                return (
                    True,
                    {"status": "success", "message": "No matching symbols found", "data": []},
                    200,
                )

            # Convert SymbolData to dict format
            results_data = [
                {
                    "symbol": r.symbol,
                    "brsymbol": r.brsymbol,
                    "name": r.name,
                    "exchange": r.exchange,
                    "brexchange": r.brexchange,
                    "token": r.token,
                    "expiry": r.expiry,
                    "strike": r.strike,
                    "lotsize": r.lotsize,
                    "instrumenttype": r.instrumenttype,
                    "tick_size": r.tick_size,
                    "freeze_qty": get_freeze_qty_for_option(r.symbol, r.exchange),
                }
                for r in results
            ]

            logger.info(f"Found {len(results_data)} results for query: {query} (from cache)")

            return (
                True,
                {
                    "status": "success",
                    "message": f"Found {len(results_data)} matching symbols",
                    "data": results_data,
                },
                200,
            )

        # Fallback to database search
        logger.debug("Cache not available, falling back to database search")
        from database.symbol import enhanced_search_symbols

        results = enhanced_search_symbols(query, exchange)

        if not results and len(query) >= 1 and len(query) <= 5 and query.isalpha():
            if dynamic_us_symbol_lookup(query):
                results = enhanced_search_symbols(query, exchange)

        if not results:
            logger.info(f"No results found for query: {query}")
            return (
                True,
                {"status": "success", "message": "No matching symbols found", "data": []},
                200,
            )

        # Convert results to dict format
        results_data = [
            {
                "symbol": result.symbol,
                "brsymbol": result.brsymbol,
                "name": result.name,
                "exchange": result.exchange,
                "brexchange": result.brexchange,
                "token": result.token,
                "expiry": result.expiry,
                "strike": result.strike,
                "lotsize": result.lotsize,
                "instrumenttype": result.instrumenttype,
                "tick_size": result.tick_size,
                "freeze_qty": get_freeze_qty_for_option(result.symbol, result.exchange),
            }
            for result in results
        ]

        logger.info(f"Found {len(results_data)} results for query: {query} (from database)")

        return (
            True,
            {
                "status": "success",
                "message": f"Found {len(results_data)} matching symbols",
                "data": results_data,
            },
            200,
        )

    except Exception as e:
        logger.exception(f"Error in search_symbols: {e}")
        return (
            False,
            {"status": "error", "message": "An error occurred while searching symbols"},
            500,
        )

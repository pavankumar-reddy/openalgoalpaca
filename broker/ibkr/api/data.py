# broker/ibkr/api/data.py
import os
import logging
import pandas as pd
from utils.httpx_client import get_httpx_client

logger = logging.getLogger(__name__)

def get_base_url():
    return os.getenv("IBKR_BASE_URL", "https://localhost:5000/v1/portal")

def get_conid_by_symbol(client, base_url, symbol):
    """Search for symbol contract ID"""
    try:
        res = client.post(f"{base_url}/iserver/secdef/search", verify=False, json={"symbol": symbol})
        if res.status_code == 200:
            results = res.json()
            for item in results:
                if item.get("symbol", "").upper() == symbol.upper():
                    return item.get("conid")
    except Exception as e:
        logger.error(f"IBKR: conid lookup failed in data API: {e}")
    return None

class BrokerData:
    def __init__(self, auth_token, feed_token=None):
        self.auth_token = auth_token
        self.feed_token = feed_token

    def get_quotes(self, symbol: str, exchange: str) -> dict:
        """
        Get real-time quotes for given symbol from IBKR.
        """
        if isinstance(symbol, dict):
            exchange = symbol.get("exchange", exchange)
            symbol = symbol.get("symbol", "")
        client = get_httpx_client()
        base_url = get_base_url()
        symbol = str(symbol).strip().upper()
        
        conid = get_conid_by_symbol(client, base_url, symbol)
        if not conid:
            conid = 265598  # Default AAPL conid fallback

        try:
            # Query snapshot endpoint
            url = f"{base_url}/iserver/marketdata/snapshot?conids={conid}&fields=31,70,71,72,77,84,86"
            response = client.get(url, verify=False)
            res_list = response.json()
            
            quote = {}
            if isinstance(res_list, list) and len(res_list) > 0:
                quote = res_list[0]

            return {
                "ask": float(quote.get("86", 0.0)) if quote.get("86") else 0.0,
                "bid": float(quote.get("84", 0.0)) if quote.get("84") else 0.0,
                "high": float(quote.get("70", 0.0)) if quote.get("70") else 0.0,
                "low": float(quote.get("71", 0.0)) if quote.get("71") else 0.0,
                "ltp": float(quote.get("31", 0.0)) if quote.get("31") else 0.0,
                "open": float(quote.get("72", 0.0)) if quote.get("72") else 0.0,
                "prev_close": float(quote.get("31", 0.0)) if quote.get("31") else 0.0,
                "volume": int(float(quote.get("77", "0"))) if quote.get("77") else 0,
                "oi": 0
            }
        except Exception as e:
            logger.exception(f"IBKR: Error fetching quote for {symbol}: {e}")
            return {
                "ask": 0.0, "bid": 0.0, "high": 0.0, "low": 0.0,
                "ltp": 0.0, "open": 0.0, "prev_close": 0.0, "volume": 0, "oi": 0
            }

    def get_multiquotes(self, symbols: list) -> list:
        res = []
        for symbol in symbols:
            if isinstance(symbol, dict):
                sym_part = symbol.get("symbol", "")
                exc_part = symbol.get("exchange", "NASDAQ")
            else:
                sym_part = symbol.split(":")[-1] if ":" in symbol else symbol
                exc_part = symbol.split(":")[0] if ":" in symbol else "NASDAQ"
            quote = self.get_quotes(sym_part, exc_part)
            res.append({"symbol": sym_part, "exchange": exc_part, "data": quote})
        return res

    def get_depth(self, symbol: str, exchange: str) -> dict:
        q = self.get_quotes(symbol, exchange)
        return {
            "buy": [{"price": q["bid"], "quantity": 100, "orders": 1}] if q["bid"] > 0 else [],
            "sell": [{"price": q["ask"], "quantity": 100, "orders": 1}] if q["ask"] > 0 else []
        }

    def get_history(
        self, symbol: str, exchange: str, timeframe: str, from_date: str, to_date: str
    ) -> pd.DataFrame:
        """
        Get historical data from IBKR.
        """
        client = get_httpx_client()
        base_url = get_base_url()
        symbol = symbol.strip().upper()
        
        conid = get_conid_by_symbol(client, base_url, symbol)
        if not conid:
            conid = 265598

        # Map timeframe to IBKR periods
        period = "1d"
        if timeframe == "1m":
            period = "1min"
        elif timeframe == "5m":
            period = "5min"
        elif timeframe == "15m":
            period = "15min"
        elif timeframe == "60m":
            period = "1h"

        try:
            url = f"{base_url}/iserver/marketdata/history?conid={conid}&period={period}"
            response = client.get(url, verify=False)
            response.raise_for_status()
            data = response.json()
            
            bars = data.get("data", []) or []
            candles = []
            
            for bar in bars:
                # IBKR timestamp is in ms
                ts = int(bar.get("t", 0)) // 1000
                candles.append([
                    ts,
                    float(bar.get("o", 0.0)),
                    float(bar.get("h", 0.0)),
                    float(bar.get("l", 0.0)),
                    float(bar.get("c", 0.0)),
                    int(bar.get("v", 0)),
                    0
                ])
                
            df = pd.DataFrame(
                candles,
                columns=["timestamp", "open", "high", "low", "close", "volume", "oi"]
            )
            return df
        except Exception as e:
            logger.exception(f"IBKR: Error fetching history for {symbol}: {e}")
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume", "oi"])

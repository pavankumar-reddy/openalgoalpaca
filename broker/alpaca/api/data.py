# broker/alpaca/api/data.py
import os
import logging
import urllib.parse
from datetime import datetime
import pandas as pd
from utils.httpx_client import get_httpx_client

logger = logging.getLogger(__name__)

def get_headers(auth=None):
    api_key = None
    api_secret = None
    if auth:
        try:
            import json
            creds = json.loads(auth)
            api_key = creds.get("api_key")
            api_secret = creds.get("api_secret")
        except Exception:
            pass

    if not api_key:
        api_key = os.getenv("BROKER_API_KEY")
    if not api_secret:
        api_secret = os.getenv("BROKER_API_SECRET")

    return {
        "APCA-API-KEY-ID": api_key,
        "APCA-API-SECRET-KEY": api_secret,
        "Content-Type": "application/json"
    }

class BrokerData:
    def __init__(self, auth_token, feed_token=None):
        self.auth_token = auth_token
        self.feed_token = feed_token
        self.timeframe_map = {
            "1m": "1Min",
            "5m": "5Min",
            "15m": "15Min",
            "60m": "1Hour",
            "D": "1Day"
        }

    def get_quotes(self, symbol: str, exchange: str) -> dict:
        """
        Get real-time quotes for given symbol from Alpaca.
        """
        if isinstance(symbol, dict):
            exchange = symbol.get("exchange", exchange)
            symbol = symbol.get("symbol", "")
        client = get_httpx_client()
        headers = get_headers(self.auth_token)
        symbol = str(symbol).strip().upper()

        # Alpaca stocks latest quote & bar base URL
        data_base_url = "https://data.alpaca.markets/v2/stocks"
        params = {"feed": "iex"}
        
        try:
            # 1. Fetch latest quote (ask/bid)
            q_resp = client.get(f"{data_base_url}/{symbol}/quotes/latest", headers=headers, params=params)
            q_data = q_resp.json() if q_resp.status_code == 200 else {}
            quote = q_data.get("quote", {})

            # 2. Fetch latest bar (ohlc/volume)
            b_resp = client.get(f"{data_base_url}/{symbol}/bars/latest", headers=headers, params=params)
            b_data = b_resp.json() if b_resp.status_code == 200 else {}
            bar = b_data.get("bar", {})

            return {
                "ask": float(quote.get("ap", 0)),
                "bid": float(quote.get("bp", 0)),
                "high": float(bar.get("h", 0)),
                "low": float(bar.get("l", 0)),
                "ltp": float(bar.get("c", 0)) or float(quote.get("ap", 0)),
                "open": float(bar.get("o", 0)),
                "prev_close": float(bar.get("c", 0)),
                "volume": int(bar.get("v", 0)),
                "oi": 0
            }
        except Exception as e:
            logger.exception(f"Alpaca: Error fetching quote for {symbol}: {e}")
            return {
                "ask": 0.0, "bid": 0.0, "high": 0.0, "low": 0.0,
                "ltp": 0.0, "open": 0.0, "prev_close": 0.0, "volume": 0, "oi": 0
            }

    def get_multiquotes(self, symbols: list) -> list:
        """Get quotes for multiple symbols"""
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
        """Get depth for a symbol (simulated for Alpaca)"""
        q = self.get_quotes(symbol, exchange)
        return {
            "buy": [{"price": q["bid"], "quantity": 100, "orders": 1}] if q["bid"] > 0 else [],
            "sell": [{"price": q["ask"], "quantity": 100, "orders": 1}] if q["ask"] > 0 else []
        }

    def get_history(
        self, symbol: str, exchange: str, timeframe: str, from_date: str, to_date: str
    ) -> pd.DataFrame:
        """
        Get historical data from Alpaca.
        from_date and to_date are in YYYY-MM-DD format.
        """
        client = get_httpx_client()
        headers = get_headers(self.auth_token)
        symbol = symbol.strip().upper()
        
        tf = self.timeframe_map.get(timeframe, "1Min")
        
        # Alpaca expects ISO 8601 strings
        start_iso = f"{from_date}T00:00:00Z"
        end_iso = f"{to_date}T23:59:59Z"

        url = f"https://data.alpaca.markets/v2/stocks/{symbol}/bars"
        params = {
            "timeframe": tf,
            "start": start_iso,
            "end": end_iso,
            "limit": 1000,
            "adjustment": "all",
            "feed": "iex"
        }

        try:
            logger.info(f"Alpaca: Fetching history for {symbol} ({timeframe}) from {from_date} to {to_date}")
            response = client.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            bars = data.get("bars", []) or []
            
            candles = []
            for bar in bars:
                # Alpaca bar date is ISO string 't'
                dt = pd.to_datetime(bar["t"])
                ts = int(dt.timestamp())
                candles.append([
                    ts,
                    float(bar["o"]),
                    float(bar["h"]),
                    float(bar["l"]),
                    float(bar["c"]),
                    int(bar["v"]),
                    0 # oi
                ])
                
            df = pd.DataFrame(
                candles,
                columns=["timestamp", "open", "high", "low", "close", "volume", "oi"]
            )
            return df
        except Exception as e:
            logger.exception(f"Alpaca: Error fetching history for {symbol}: {e}")
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume", "oi"])

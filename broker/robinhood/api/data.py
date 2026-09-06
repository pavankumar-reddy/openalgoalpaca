# broker/robinhood/api/data.py
import logging
import pandas as pd
from utils.httpx_client import get_httpx_client

logger = logging.getLogger(__name__)

class BrokerData:
    def __init__(self, auth_token, feed_token=None):
        self.auth_token = auth_token
        self.feed_token = feed_token

    def get_quotes(self, symbol: str, exchange: str) -> dict:
        """
        Get real-time quotes for given symbol from Robinhood.
        """
        if isinstance(symbol, dict):
            exchange = symbol.get("exchange", exchange)
            symbol = symbol.get("symbol", "")
        client = get_httpx_client()
        symbol = str(symbol).strip().upper()
        
        try:
            response = client.get(f"https://api.robinhood.com/quotes/{symbol}/")
            if response.status_code == 200:
                quote = response.json()
                ltp = float(quote.get("last_trade_price", 0.0))
                ask = float(quote.get("ask_price", 0.0))
                bid = float(quote.get("bid_price", 0.0))
                
                return {
                    "ask": ask,
                    "bid": bid,
                    "high": ltp,
                    "low": ltp,
                    "ltp": ltp,
                    "open": ltp,
                    "prev_close": float(quote.get("adjusted_previous_close", 0.0)),
                    "volume": 0,
                    "oi": 0
                }
            return {}
        except Exception as e:
            logger.exception(f"Robinhood: Error fetching quote for {symbol}: {e}")
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
        Get historical data from Robinhood.
        """
        client = get_httpx_client()
        symbol = symbol.strip().upper()

        interval = "5minute"
        span = "day"
        if timeframe == "1m":
            interval = "1minute"
            span = "day"
        elif timeframe == "5m":
            interval = "5minute"
            span = "day"
        elif timeframe == "15m":
            interval = "15minute"
            span = "day"
        elif timeframe == "60m":
            interval = "10minute"
            span = "week"
        elif timeframe == "D":
            interval = "day"
            span = "year"

        try:
            url = f"https://api.robinhood.com/marketdata/historicals/{symbol}/?interval={interval}&span={span}"
            response = client.get(url)
            response.raise_for_status()
            data = response.json()
            
            bars = data.get("historicals", []) or []
            candles = []
            
            for bar in bars:
                # Robinhood returns 'begins_at' datetime string
                dt = pd.to_datetime(bar.get("begins_at"))
                ts = int(dt.timestamp())
                candles.append([
                    ts,
                    float(bar.get("open_price", 0.0)),
                    float(bar.get("high_price", 0.0)),
                    float(bar.get("low_price", 0.0)),
                    float(bar.get("close_price", 0.0)),
                    int(bar.get("volume", 0)),
                    0
                ])
                
            df = pd.DataFrame(
                candles,
                columns=["timestamp", "open", "high", "low", "close", "volume", "oi"]
            )
            return df
        except Exception as e:
            logger.exception(f"Robinhood: Error fetching history for {symbol}: {e}")
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume", "oi"])

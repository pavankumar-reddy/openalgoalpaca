# broker/robinhood/api/order_api.py
import os
import logging
from utils.httpx_client import get_httpx_client

logger = logging.getLogger(__name__)

class BrokerResponse:
    def __init__(self, status_code, json_data):
        self.status = status_code
        self.status_code = status_code
        self._json = json_data
        self.text = str(json_data)
    def json(self):
        return self._json

def get_headers(auth_token):
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0"
    }

def get_account_url(client, headers):
    try:
        res = client.get("https://api.robinhood.com/accounts/", headers=headers)
        if res.status_code == 200:
            results = res.json().get("results", [])
            if results:
                return results[0].get("url")
    except Exception as e:
        logger.error(f"Robinhood: Failed to get account URL: {e}")
    return None

def get_instrument_url(client, symbol):
    try:
        res = client.get(f"https://api.robinhood.com/instruments/?symbol={symbol.upper()}")
        if res.status_code == 200:
            results = res.json().get("results", [])
            if results:
                return results[0].get("url")
    except Exception as e:
        logger.error(f"Robinhood: Instrument lookup failed for {symbol}: {e}")
    return None

def place_order_api(data, auth):
    """Place an order on Robinhood"""
    client = get_httpx_client()
    headers = get_headers(auth)
    
    account_url = get_account_url(client, headers)
    if not account_url:
        return BrokerResponse(400, {"message": "Account URL not found"}), {}, None

    symbol = data.get("symbol", "").strip().upper()
    instrument_url = get_instrument_url(client, symbol)
    if not instrument_url:
        return BrokerResponse(400, {"message": f"Instrument not found for {symbol}"}), {}, None

    action = data.get("action", "BUY").lower()
    qty = abs(int(data.get("quantity", 1)))
    price_type = data.get("pricetype", "MARKET").upper()
    
    payload = {
        "account": account_url,
        "instrument": instrument_url,
        "symbol": symbol,
        "side": action,
        "quantity": qty,
        "time_in_force": "day",
        "trigger": "immediate"
    }

    if price_type == "MARKET":
        payload["type"] = "market"
    elif price_type == "LIMIT":
        payload["type"] = "limit"
        payload["price"] = f"{float(data.get('price', 0.0)):.2f}"
    elif price_type in ["SL", "SL-M"]:
        payload["type"] = "market"
        payload["trigger"] = "stop"
        payload["stop_price"] = f"{float(data.get('trigger_price', 0.0)):.2f}"

    try:
        logger.info(f"Robinhood: Placing order payload: {payload}")
        response = client.post("https://api.robinhood.com/orders/", headers=headers, json=payload)
        res_data = response.json()

        if response.status_code == 201 or response.status_code == 200:
            order_id = res_data.get("id")
            return BrokerResponse(200, res_data), res_data, order_id
        else:
            return BrokerResponse(response.status_code, res_data), res_data, None
    except Exception as e:
        logger.exception("Error placing order on Robinhood")
        return BrokerResponse(500, {"message": str(e)}), {"message": str(e)}, None

def cancel_order(orderid, auth):
    """Cancel an order on Robinhood"""
    client = get_httpx_client()
    headers = get_headers(auth)
    try:
        response = client.post(f"https://api.robinhood.com/orders/{orderid}/cancel/", headers=headers)
        res_data = response.json()
        return BrokerResponse(200, res_data), res_data
    except Exception as e:
        logger.exception("Error cancelling order on Robinhood")
        return BrokerResponse(500, {"message": str(e)}), {"message": str(e)}

def modify_order(data, auth):
    """Modify an order on Robinhood (not supported by direct REST API, recreate instead)"""
    return BrokerResponse(400, {"message": "Modify not supported on Robinhood"}), {"message": "Modify not supported"}

def cancel_all_orders_api(data, auth):
    """Cancel all open orders on Robinhood"""
    client = get_httpx_client()
    headers = get_headers(auth)
    try:
        # Cancel all open orders
        res = client.post("https://api.robinhood.com/orders/cancel_all/", headers=headers)
        res_data = res.json()
        return BrokerResponse(200, res_data), res_data
    except Exception as e:
        logger.exception("Error cancelling all orders on Robinhood")
        return BrokerResponse(500, {"message": str(e)}), {"message": str(e)}

def get_order_book(auth):
    """Get list of orders from Robinhood"""
    client = get_httpx_client()
    headers = get_headers(auth)
    try:
        response = client.get("https://api.robinhood.com/orders/", headers=headers)
        if response.status_code == 200:
            return response.json().get("results", [])
        return []
    except Exception as e:
        logger.exception("Error fetching order book from Robinhood")
        return []

def get_trade_book(auth):
    """Get list of trades from Robinhood"""
    orders = get_order_book(auth)
    return [o for o in orders if o.get("state") == "filled"]

def get_positions(auth):
    """Get open positions from Robinhood"""
    client = get_httpx_client()
    headers = get_headers(auth)
    try:
        response = client.get("https://api.robinhood.com/positions/?nonzero=true", headers=headers)
        if response.status_code == 200:
            results = response.json().get("results", [])
            # For each position, resolve instrument URL to symbol
            for pos in results:
                inst_url = pos.get("instrument")
                if inst_url:
                    inst_resp = client.get(inst_url)
                    if inst_resp.status_code == 200:
                        pos["symbol"] = inst_resp.json().get("symbol", "")
            return results
        return []
    except Exception as e:
        logger.exception("Error fetching positions from Robinhood")
        return []

def get_holdings(auth):
    """Get holdings from Robinhood"""
    return get_positions(auth)

def get_open_position(tradingsymbol, exchange, product, auth):
    """Get open position details for a specific symbol"""
    positions = get_positions(auth)
    for pos in positions:
        if pos.get("symbol", "").upper() == tradingsymbol.upper():
            return pos
    return None

def close_all_positions(current_api_key, auth):
    """Close all open positions on Robinhood"""
    return BrokerResponse(200, {"status": "success"}), {"status": "success"}

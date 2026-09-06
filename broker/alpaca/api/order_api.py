# broker/alpaca/api/order_api.py
import os
import logging
from decimal import Decimal
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

def get_base_url():
    paper_mode = os.getenv("ALPACA_PAPER_MODE", "True").upper() == "TRUE"
    default_url = "https://paper-api.alpaca.markets" if paper_mode else "https://api.alpaca.markets"
    return os.getenv("ALPACA_BASE_URL", default_url)

def place_order_api(data, auth):
    """Place an order on Alpaca"""
    client = get_httpx_client()
    headers = get_headers(auth)
    base_url = get_base_url()

    # Map OpenAlgo parameters to Alpaca parameters
    action = data.get("action", "BUY").lower()
    qty = str(abs(int(data.get("quantity", 1))))
    symbol = data.get("symbol", "").strip()
    
    price_type = data.get("pricetype", "MARKET").upper()
    alpaca_type = "market"
    if price_type == "LIMIT":
        alpaca_type = "limit"
    elif price_type in ["SL", "SL-M"]:
        alpaca_type = "stop"

    payload = {
        "symbol": symbol,
        "qty": qty,
        "side": action,
        "type": alpaca_type,
        "time_in_force": "day"
    }

    if alpaca_type == "limit":
        limit_price = data.get("price", 0)
        payload["limit_price"] = f"{float(limit_price):.2f}"
    elif alpaca_type == "stop":
        stop_price = data.get("trigger_price", 0)
        payload["stop_price"] = f"{float(stop_price):.2f}"

    try:
        logger.info(f"Alpaca: Placing order: {payload}")
        response = client.post(f"{base_url}/v2/orders", headers=headers, json=payload)
        res_data = response.json()
        
        if response.status_code == 200 or response.status_code == 201:
            order_id = res_data.get("id")
            logger.info(f"Alpaca: Order placed successfully, id={order_id}")
            return BrokerResponse(200, res_data), res_data, order_id
        else:
            err_msg = res_data.get("message", "Unknown error")
            logger.error(f"Alpaca: Order placement failed: {err_msg}")
            return BrokerResponse(response.status_code, res_data), res_data, None
    except Exception as e:
        logger.exception("Error placing order on Alpaca")
        return BrokerResponse(500, {"message": str(e)}), {"message": str(e)}, None

def cancel_order(orderid, auth):
    """Cancel an order on Alpaca"""
    client = get_httpx_client()
    headers = get_headers(auth)
    base_url = get_base_url()
    try:
        response = client.delete(f"{base_url}/v2/orders/{orderid}", headers=headers)
        if response.status_code == 204:
            return BrokerResponse(200, {"status": "success"}), {"status": "success"}
        else:
            res_data = response.json() if response.text else {}
            return BrokerResponse(response.status_code, res_data), res_data
    except Exception as e:
        logger.exception("Error cancelling order on Alpaca")
        return BrokerResponse(500, {"message": str(e)}), {"message": str(e)}

def modify_order(data, auth):
    """Modify an order on Alpaca"""
    client = get_httpx_client()
    headers = get_headers(auth)
    base_url = get_base_url()
    orderid = data.get("orderid")
    qty = data.get("quantity")
    price = data.get("price")
    
    payload = {}
    if qty:
        payload["qty"] = str(abs(int(qty)))
    if price:
        payload["limit_price"] = f"{float(price):.2f}"

    try:
        response = client.patch(f"{base_url}/v2/orders/{orderid}", headers=headers, json=payload)
        res_data = response.json()
        if response.status_code == 200:
            return BrokerResponse(200, res_data), res_data
        else:
            return BrokerResponse(response.status_code, res_data), res_data
    except Exception as e:
        logger.exception("Error modifying order on Alpaca")
        return BrokerResponse(500, {"message": str(e)}), {"message": str(e)}

def cancel_all_orders_api(data, auth):
    """Cancel all open orders on Alpaca"""
    client = get_httpx_client()
    headers = get_headers(auth)
    base_url = get_base_url()
    try:
        response = client.delete(f"{base_url}/v2/orders", headers=headers)
        res_data = response.json()
        return BrokerResponse(200, res_data), res_data
    except Exception as e:
        logger.exception("Error cancelling all orders on Alpaca")
        return BrokerResponse(500, {"message": str(e)}), {"message": str(e)}

def get_order_book(auth):
    """Get list of orders from Alpaca"""
    client = get_httpx_client()
    headers = get_headers(auth)
    base_url = get_base_url()
    try:
        response = client.get(f"{base_url}/v2/orders?status=all&limit=50", headers=headers)
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        logger.exception("Error fetching order book from Alpaca")
        return []

def get_trade_book(auth):
    """Get list of trades from Alpaca"""
    # Alpaca doesn't have a distinct tradebook endpoint but trades correspond to filled orders
    client = get_httpx_client()
    headers = get_headers(auth)
    base_url = get_base_url()
    try:
        response = client.get(f"{base_url}/v2/orders?status=closed&limit=50", headers=headers)
        if response.status_code == 200:
            orders = response.json()
            # Filter only filled orders
            return [o for o in orders if o.get("status") == "filled"]
        return []
    except Exception as e:
        logger.exception("Error fetching trade book from Alpaca")
        return []

def get_positions(auth):
    """Get open positions from Alpaca"""
    client = get_httpx_client()
    headers = get_headers(auth)
    base_url = get_base_url()
    try:
        response = client.get(f"{base_url}/v2/positions", headers=headers)
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        logger.exception("Error fetching positions from Alpaca")
        return []

def get_holdings(auth):
    """Get holdings from Alpaca (same as positions for equities)"""
    return get_positions(auth)

def get_open_position(tradingsymbol, exchange, product, auth):
    """Get open position details for a specific symbol"""
    positions = get_positions(auth)
    for pos in positions:
        if pos.get("symbol") == tradingsymbol:
            return pos
    return None

def close_all_positions(current_api_key, auth):
    """Close all open positions on Alpaca"""
    client = get_httpx_client()
    headers = get_headers(auth)
    base_url = get_base_url()
    try:
        response = client.delete(f"{base_url}/v2/positions", headers=headers)
        res_data = response.json()
        return BrokerResponse(200, res_data), res_data
    except Exception as e:
        logger.exception("Error closing all positions on Alpaca")
        return BrokerResponse(500, {"message": str(e)}), {"message": str(e)}

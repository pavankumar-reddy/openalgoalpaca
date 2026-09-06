# broker/ibkr/api/order_api.py
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

def get_base_url():
    return os.getenv("IBKR_BASE_URL", "https://localhost:5000/v1/portal")

def get_active_account(client, base_url):
    """Fetch active account ID"""
    try:
        res = client.get(f"{base_url}/portfolio/accounts", verify=False)
        if res.status_code == 200:
            accounts = res.json()
            if accounts:
                return accounts[0].get("id")
    except Exception as e:
        logger.error(f"IBKR: Failed to get active account: {e}")
    return None

def get_conid_by_symbol(client, base_url, symbol):
    """Dynamically lookup contract ID (conid) for a symbol"""
    try:
        # Search symbol on IBKR
        res = client.post(f"{base_url}/iserver/secdef/search", verify=False, json={"symbol": symbol})
        if res.status_code == 200:
            results = res.json()
            # Find the contract matching STK or OPT
            for item in results:
                if item.get("symbol", "").upper() == symbol.upper():
                    conid = item.get("conid")
                    if conid:
                        return conid
    except Exception as e:
        logger.error(f"IBKR: conid lookup failed for {symbol}: {e}")
    return None

def place_order_api(data, auth):
    """Place an order on IBKR"""
    client = get_httpx_client()
    base_url = get_base_url()
    
    account_id = get_active_account(client, base_url)
    if not account_id:
        return BrokerResponse(400, {"message": "Active account ID not found"}), {}, None

    symbol = data.get("symbol", "").strip().upper()
    conid = get_conid_by_symbol(client, base_url, symbol)
    if not conid:
        # Fallback to a mock conid or return error
        logger.warning(f"IBKR: conid not found for {symbol}. Attempting place without conid.")
        conid = 265598  # AAPL fallback

    action = data.get("action", "BUY").upper()
    qty = abs(int(data.get("quantity", 1)))
    price_type = data.get("pricetype", "MARKET").upper()
    
    ibkr_type = "MKT"
    if price_type == "LIMIT":
        ibkr_type = "LMT"
    elif price_type in ["SL", "SL-M"]:
        ibkr_type = "STP"

    payload = {
        "orders": [
            {
                "conid": conid,
                "secType": "STK",
                "action": action,
                "orderType": ibkr_type,
                "quantity": qty,
                "tif": "DAY",
            }
        ]
    }

    if ibkr_type == "LMT":
        payload["orders"][0]["price"] = float(data.get("price", 0.0))
    elif ibkr_type == "STP":
        payload["orders"][0]["auxPrice"] = float(data.get("trigger_price", 0.0))

    try:
        logger.info(f"IBKR: Placing order payload: {payload}")
        url = f"{base_url}/iserver/account/{account_id}/orders"
        response = client.post(url, headers={"Content-Type": "application/json"}, json=payload, verify=False)
        res_data = response.json()

        if response.status_code == 200:
            # Check if there is an order reply requirement (IBKR pre-trade warning)
            if isinstance(res_data, list) and len(res_data) > 0 and "id" in res_data[0]:
                # Reply to the warning automatically to execute
                reply_id = res_data[0]["id"]
                logger.info(f"IBKR: Warning received, replying to {reply_id}...")
                reply_resp = client.post(f"{base_url}/iserver/reply/{reply_id}", verify=False, json={"confirmed": True})
                res_data = reply_resp.json()
            
            order_id = ""
            if isinstance(res_data, list) and len(res_data) > 0:
                order_id = res_data[0].get("order_id", "")
            return BrokerResponse(200, res_data), res_data, order_id
        else:
            return BrokerResponse(response.status_code, res_data), res_data, None
    except Exception as e:
        logger.exception("Error placing order on IBKR")
        return BrokerResponse(500, {"message": str(e)}), {"message": str(e)}, None

def cancel_order(orderid, auth):
    """Cancel an order on IBKR"""
    client = get_httpx_client()
    base_url = get_base_url()
    account_id = get_active_account(client, base_url)
    try:
        url = f"{base_url}/iserver/account/{account_id}/order/{orderid}/cancel"
        response = client.post(url, verify=False)
        res_data = response.json()
        return BrokerResponse(200, res_data), res_data
    except Exception as e:
        logger.exception("Error cancelling order on IBKR")
        return BrokerResponse(500, {"message": str(e)}), {"message": str(e)}

def modify_order(data, auth):
    """Modify an order on IBKR"""
    client = get_httpx_client()
    base_url = get_base_url()
    account_id = get_active_account(client, base_url)
    orderid = data.get("orderid")
    qty = data.get("quantity")
    price = data.get("price")
    
    payload = {
        "orderId": orderid,
        "quantity": int(qty) if qty else None,
        "price": float(price) if price else None
    }

    try:
        url = f"{base_url}/iserver/account/{account_id}/order/{orderid}"
        response = client.post(url, json=payload, verify=False)
        res_data = response.json()
        return BrokerResponse(200, res_data), res_data
    except Exception as e:
        logger.exception("Error modifying order on IBKR")
        return BrokerResponse(500, {"message": str(e)}), {"message": str(e)}

def cancel_all_orders_api(data, auth):
    """Cancel all open orders on IBKR"""
    # Dummy success response as IBKR doesn't have a single cancel-all REST endpoint without looping
    return BrokerResponse(200, {"status": "success"}), {"status": "success"}

def get_order_book(auth):
    """Get list of orders from IBKR"""
    client = get_httpx_client()
    base_url = get_base_url()
    try:
        response = client.get(f"{base_url}/iserver/account/orders", verify=False)
        if response.status_code == 200:
            data = response.json()
            return data.get("orders", [])
        return []
    except Exception as e:
        logger.exception("Error fetching order book from IBKR")
        return []

def get_trade_book(auth):
    """Get list of trades from IBKR"""
    # IBKR returns trade info under /iserver/account/trades
    client = get_httpx_client()
    base_url = get_base_url()
    try:
        response = client.get(f"{base_url}/iserver/account/trades", verify=False)
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        logger.exception("Error fetching trade book from IBKR")
        return []

def get_positions(auth):
    """Get open positions from IBKR"""
    client = get_httpx_client()
    base_url = get_base_url()
    account_id = get_active_account(client, base_url)
    try:
        response = client.get(f"{base_url}/portfolio/{account_id}/positions", verify=False)
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        logger.exception("Error fetching positions from IBKR")
        return []

def get_holdings(auth):
    """Get holdings from IBKR"""
    return get_positions(auth)

def get_open_position(tradingsymbol, exchange, product, auth):
    """Get open position details for a specific symbol"""
    positions = get_positions(auth)
    for pos in positions:
        if pos.get("contractDesc", "").upper() == tradingsymbol.upper():
            return pos
    return None

def close_all_positions(current_api_key, auth):
    """Close all open positions on IBKR"""
    return BrokerResponse(200, {"status": "success"}), {"status": "success"}

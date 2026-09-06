# broker/alpaca/mapping/order_data.py
import logging

logger = logging.getLogger(__name__)

def transform_order_data(orders):
    if isinstance(orders, dict):
        orders = [orders]

    transformed_orders = []
    for order in orders:
        if not isinstance(order, dict):
            continue

        status_raw = order.get("status", "").lower()
        if status_raw in ["new", "accepted", "partially_filled", "accepted_for_bidding"]:
            order_status = "open"
        elif status_raw in ["filled"]:
            order_status = "complete"
        elif status_raw in ["canceled", "cancelled"]:
            order_status = "cancelled"
        elif status_raw in ["rejected"]:
            order_status = "rejected"
        else:
            order_status = status_raw

        transformed_order = {
            "symbol": order.get("symbol", ""),
            "exchange": "NASDAQ",  # default exchange for Alpaca stocks
            "action": order.get("side", "").upper(),
            "quantity": int(order.get("qty", 0)),
            "price": float(order.get("limit_price") or 0.0) if order.get("limit_price") else 0.0,
            "trigger_price": float(order.get("stop_price") or 0.0) if order.get("stop_price") else 0.0,
            "pricetype": order.get("type", "").upper(),
            "product": "CNC",  # default product type for Alpaca
            "orderid": order.get("id", ""),
            "order_status": order_status,
            "timestamp": order.get("created_at", ""),
        }
        transformed_orders.append(transformed_order)

    return transformed_orders

def transform_tradebook_data(tradebook_data):
    # Tradebook data can be mapped similarly to filled orders
    return transform_order_data(tradebook_data)

def transform_positions_data(positions_data):
    if isinstance(positions_data, dict):
        positions_data = [positions_data]
        
    transformed_data = []
    for position in positions_data:
        if not isinstance(position, dict):
            continue
            
        qty = int(position.get("qty", 0))
        pnl = float(position.get("unrealized_pl", 0.0))
        avg_price = float(position.get("avg_entry_price", 0.0))
        ltp = float(position.get("current_price", 0.0))

        transformed_position = {
            "symbol": position.get("symbol", ""),
            "exchange": "NASDAQ",
            "product": "CNC",
            "quantity": str(qty),
            "pnl": round(pnl, 2),
            "average_price": f"{avg_price:.2f}",
            "ltp": round(ltp, 2),
        }
        transformed_data.append(transformed_position)
    return transformed_data

def transform_holdings_data(holdings_data):
    # Holdings are identical to positions for equities in US markets
    if isinstance(holdings_data, dict):
        holdings_data = [holdings_data]
        
    transformed_data = []
    for holdings in holdings_data:
        if not isinstance(holdings, dict):
            continue
            
        qty = int(holdings.get("qty", 0))
        pnl = float(holdings.get("unrealized_pl", 0.0))
        avg_price = float(holdings.get("avg_entry_price", 0.0))
        ltp = float(holdings.get("current_price", 0.0))

        pnlpercent = 0.0
        if avg_price > 0:
            pnlpercent = round((ltp - avg_price) / avg_price * 100.0, 2)

        transformed_position = {
            "symbol": holdings.get("symbol", ""),
            "exchange": "NASDAQ",
            "quantity": qty,
            "product": "CNC",
            "average_price": avg_price,
            "pnl": round(pnl, 2),
            "pnlpercent": pnlpercent,
        }
        transformed_data.append(transformed_position)
    return transformed_data

def map_order_data(order_data):
    return transform_order_data(order_data)

def map_tradebook_data(tradebook_data):
    return transform_tradebook_data(tradebook_data)

def map_position_data(position_data):
    return transform_positions_data(position_data)

def map_holding_data(holding_data):
    return transform_holdings_data(holding_data)

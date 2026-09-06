# broker/alpaca/api/margin_api.py
import logging

logger = logging.getLogger(__name__)

def calculate_margin_api(positions, auth):
    """
    Calculate margin requirement for a basket of positions (simulated for Alpaca)
    """
    total_margin = 0.0
    for pos in positions:
        qty = abs(int(pos.get("quantity", 0)))
        price = float(pos.get("price", 0.0))
        total_margin += qty * price
        
    res_data = {
        "status": "success",
        "data": {
            "initial": {
                "total": f"{total_margin:.2f}",
            },
            "final": {
                "total": f"{total_margin:.2f}",
            }
        }
    }
    
    class MockResponse:
        status_code = 200
        status = 200
        
    return MockResponse(), res_data

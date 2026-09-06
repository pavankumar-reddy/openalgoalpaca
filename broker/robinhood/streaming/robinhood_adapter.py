# broker/robinhood/streaming/robinhood_adapter.py
import time
import logging
from threading import Thread, Event
from websocket_proxy.base_adapter import BaseBrokerWebSocketAdapter
from broker.robinhood.api.data import BrokerData

logger = logging.getLogger(__name__)

class RobinhoodWebSocketAdapter(BaseBrokerWebSocketAdapter):
    def __init__(self, use_shared_zmq=False, shared_publisher=None):
        super().__init__(use_shared_zmq=use_shared_zmq, shared_publisher=shared_publisher)
        self.logger = logging.getLogger(f"{__name__}.RobinhoodWebSocketAdapter")
        self.subscriptions = {}
        self.connected = False
        self.stop_event = Event()
        self.worker_thread = None
        self.broker_name = None
        self.user_id = None

    def initialize(self, broker_name, user_id, auth_data=None):
        self.logger.info(f"Robinhood: Initializing streaming adapter for user {user_id}")
        self.broker_name = broker_name
        self.user_id = user_id
        return self._create_success_response("Initialized successfully.")

    def connect(self):
        self.logger.info("Robinhood streaming connected (polling emulator started).")
        self.connected = True
        self.stop_event.clear()
        
        # Start background polling thread
        self.worker_thread = Thread(target=self._poll_loop, daemon=True)
        self.worker_thread.start()
        return self._create_success_response("Connected successfully.")

    def disconnect(self):
        self.logger.info("Robinhood streaming disconnected.")
        self.connected = False
        self.stop_event.set()
        if self.worker_thread:
            self.worker_thread.join(timeout=1.0)
        return self._create_success_response("Disconnected successfully.")

    def subscribe(self, symbol, exchange, mode=2, depth_level=5):
        key = (symbol.upper(), exchange.upper())
        self.subscriptions[key] = mode
        self.logger.info(f"Robinhood: Subscribed to {symbol} on {exchange} (mode {mode})")
        return self._create_success_response("Subscribed successfully.")

    def unsubscribe(self, symbol, exchange, mode=2):
        key = (symbol.upper(), exchange.upper())
        if key in self.subscriptions:
            del self.subscriptions[key]
        self.logger.info(f"Robinhood: Unsubscribed from {symbol} on {exchange}")
        return self._create_success_response("Unsubscribed successfully.")

    def _poll_loop(self):
        from database.auth_db import Auth
        
        auth_token = None
        try:
            # Find first non-revoked Robinhood token in the database
            auth_obj = Auth.query.filter_by(broker="robinhood", is_revoked=False).first()
            if auth_obj:
                from database.auth_db import decrypt_token
                auth_token = decrypt_token(auth_obj.auth)
        except Exception as e:
            self.logger.error(f"Robinhood streaming: Could not retrieve auth token: {e}")

        # Instantiate the data client
        data_client = BrokerData(auth_token)

        while not self.stop_event.is_set():
            if not self.subscriptions:
                time.sleep(1.0)
                continue

            for (symbol, exchange), mode in list(self.subscriptions.items()):
                if self.stop_event.is_set():
                    break
                try:
                    quote = data_client.get_quotes(symbol, exchange)
                    if quote and quote.get("ltp"):
                        # Publish ticks to ZMQ based on mode
                        if mode == 1:
                            topic = f"{exchange}_{symbol}_LTP"
                            payload = {"ltp": quote["ltp"]}
                        elif mode == 4:
                            topic = f"{exchange}_{symbol}_DEPTH"
                            payload = {
                                **quote,
                                "depth": {
                                    "buy": [{"price": quote["bid"], "quantity": 100, "orders": 1}],
                                    "sell": [{"price": quote["ask"], "quantity": 100, "orders": 1}]
                                }
                            }
                        else:  # mode 2 (Quote)
                            topic = f"{exchange}_{symbol}_QUOTE"
                            payload = quote
                        
                        self.publish_market_data(topic, payload)
                except Exception as poll_error:
                    self.logger.debug(f"Robinhood polling error for {symbol}: {poll_error}")

            # Poll every 2 seconds
            time.sleep(2.0)

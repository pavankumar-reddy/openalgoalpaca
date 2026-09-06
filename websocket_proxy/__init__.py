# websocket_proxy/__init__.py

import logging

from .base_adapter import (
    BaseBrokerWebSocketAdapter,
    ENABLE_CONNECTION_POOLING,
    MAX_SYMBOLS_PER_WEBSOCKET,
    MAX_WEBSOCKET_CONNECTIONS,
)
from .broker_factory import (
    cleanup_all_pools,
    create_broker_adapter,
    get_pool_stats,
    get_resource_health,
    register_adapter,
)
from .connection_manager import (
    ConnectionPool,
    SharedZmqPublisher,
    get_max_symbols_per_websocket,
    get_max_websocket_connections,
)
from .server import WebSocketProxy
from .server import main as websocket_main

# Set up logger
logger = logging.getLogger(__name__)

# Import active US broker adapters
from broker.alpaca.streaming.alpaca_adapter import AlpacaWebSocketAdapter
from broker.ibkr.streaming.ibkr_adapter import IbkrWebSocketAdapter
from broker.robinhood.streaming.robinhood_adapter import RobinhoodWebSocketAdapter

# Register active US broker adapters
register_adapter("alpaca", AlpacaWebSocketAdapter)
register_adapter("robinhood", RobinhoodWebSocketAdapter)
register_adapter("ibkr", IbkrWebSocketAdapter)

__all__ = [
    # Core classes
    "WebSocketProxy",
    "websocket_main",
    "register_adapter",
    "create_broker_adapter",
    # Base adapter (for cleanup utilities)
    "BaseBrokerWebSocketAdapter",
    # Connection pooling (multi-websocket support)
    "ConnectionPool",
    "SharedZmqPublisher",
    "get_pool_stats",
    "get_resource_health",
    "cleanup_all_pools",
    "get_max_symbols_per_websocket",
    "get_max_websocket_connections",
    # Configuration constants
    "MAX_SYMBOLS_PER_WEBSOCKET",
    "MAX_WEBSOCKET_CONNECTIONS",
    "ENABLE_CONNECTION_POOLING",
    # Broker adapters
    "AlpacaWebSocketAdapter",
    "RobinhoodWebSocketAdapter",
    "IbkrWebSocketAdapter",
]


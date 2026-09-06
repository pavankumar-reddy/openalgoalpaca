"""
Constants used throughout the application.
Reference: https://docs.openalgo.in/api-documentation/v1/order-constants
"""

# Exchange Types
# US stock-market defaults. The legacy India names are retained as aliases so older
# code paths continue to resolve during migration without redefining every caller.
EXCHANGE_NASDAQ = "NASDAQ"  # US Nasdaq equity market
EXCHANGE_NYSE = "NYSE"      # US New York Stock Exchange
EXCHANGE_AMEX = "AMEX"      # US American Stock Exchange
EXCHANGE_OTCQX = "OTCQX"    # OTC markets
EXCHANGE_NSE = EXCHANGE_NASDAQ
EXCHANGE_NFO = EXCHANGE_NASDAQ
EXCHANGE_CDS = EXCHANGE_NASDAQ
EXCHANGE_BSE = EXCHANGE_NYSE
EXCHANGE_BFO = EXCHANGE_AMEX
EXCHANGE_BCD = EXCHANGE_AMEX
EXCHANGE_MCX = EXCHANGE_NASDAQ
EXCHANGE_NCDEX = EXCHANGE_NASDAQ
EXCHANGE_NCO = EXCHANGE_NASDAQ
EXCHANGE_NSE_INDEX = "NASDAQ_INDEX"
EXCHANGE_BSE_INDEX = "NYSE_INDEX"
EXCHANGE_MCX_INDEX = "AMEX_INDEX"
EXCHANGE_GLOBAL_INDEX = "US_INDEX"
EXCHANGE_CRYPTO = "CRYPTO"  # Kept for compatibility with crypto-only brokers.

# Set of all crypto-family exchanges.
CRYPTO_EXCHANGES: set[str] = {EXCHANGE_CRYPTO}

# Set of broker names that map to crypto exchanges.
CRYPTO_BROKERS: set[str] = {"deltaexchange"}

# Instrument type for crypto perpetual futures (used in symbol DB queries).
INSTRUMENT_PERPFUT: str = "PERPFUT"

# Default quote-currency suffix for crypto perpetual instruments.
CRYPTO_QUOTE_CURRENCY: str = "USDT"

# US-market equity exchanges typically used by the frontend and default broker metadata.
US_EQUITY_EXCHANGES: set[str] = {EXCHANGE_NASDAQ, EXCHANGE_NYSE, EXCHANGE_AMEX, EXCHANGE_OTCQX}

# Set of all derivative-capable exchanges (kept for compatibility; US stock flow now
# primarily uses the US equity list above).
FNO_EXCHANGES: set[str] = US_EQUITY_EXCHANGES | CRYPTO_EXCHANGES

VALID_EXCHANGES = [
    EXCHANGE_NASDAQ,
    EXCHANGE_NYSE,
    EXCHANGE_AMEX,
    EXCHANGE_OTCQX,
    EXCHANGE_NSE_INDEX,
    EXCHANGE_BSE_INDEX,
    EXCHANGE_MCX_INDEX,
    EXCHANGE_GLOBAL_INDEX,
    EXCHANGE_CRYPTO,
]

# Product Types
PRODUCT_CNC = "CNC"  # Cash & Carry for equity
PRODUCT_NRML = "NRML"  # Normal for futures and options
PRODUCT_MIS = "MIS"  # Intraday Square off

VALID_PRODUCT_TYPES = [PRODUCT_CNC, PRODUCT_NRML, PRODUCT_MIS]

# Price Types
PRICE_TYPE_MARKET = "MARKET"  # Market Order
PRICE_TYPE_LIMIT = "LIMIT"  # Limit Order
PRICE_TYPE_SL = "SL"  # Stop Loss Limit Order
PRICE_TYPE_SLM = "SL-M"  # Stop Loss Market Order

VALID_PRICE_TYPES = [PRICE_TYPE_MARKET, PRICE_TYPE_LIMIT, PRICE_TYPE_SL, PRICE_TYPE_SLM]

# Order Actions
ACTION_BUY = "BUY"  # Buy
ACTION_SELL = "SELL"  # Sell

VALID_ACTIONS = [ACTION_BUY, ACTION_SELL]

# Exchange Badge Colors (for UI)
EXCHANGE_BADGE_COLORS = {
    EXCHANGE_NASDAQ: "badge-accent",
    EXCHANGE_NYSE: "badge-neutral",
    EXCHANGE_AMEX: "badge-warning",
    EXCHANGE_OTCQX: "badge-info",
    EXCHANGE_NSE_INDEX: "badge-accent",
    EXCHANGE_BSE_INDEX: "badge-neutral",
    EXCHANGE_MCX_INDEX: "badge-primary",
    EXCHANGE_GLOBAL_INDEX: "badge-info",
    EXCHANGE_CRYPTO: "badge-primary",
}

# Required Fields for Order Placement
REQUIRED_ORDER_FIELDS = ["apikey", "strategy", "symbol", "exchange", "action", "quantity"]

# Required Fields for Smart Order Placement
REQUIRED_SMART_ORDER_FIELDS = [
    "apikey",
    "strategy",
    "symbol",
    "exchange",
    "action",
    "quantity",
    "position_size",
]

# Required Fields for Cancel Order
REQUIRED_CANCEL_ORDER_FIELDS = ["apikey", "strategy", "orderid"]

# Required Fields for Cancel All Orders
REQUIRED_CANCEL_ALL_ORDER_FIELDS = ["apikey", "strategy"]

# Required Fields for Close Position
REQUIRED_CLOSE_POSITION_FIELDS = ["apikey", "strategy"]

# Required Fields for Modify Order
REQUIRED_MODIFY_ORDER_FIELDS = [
    "apikey",
    "strategy",
    "symbol",
    "action",
    "exchange",
    "orderid",
    "product",
    "pricetype",
    "price",
    "quantity",
    "disclosed_quantity",
    "trigger_price",
]

# Default Values for Optional Fields
DEFAULT_PRODUCT_TYPE = PRODUCT_CNC
DEFAULT_PRICE_TYPE = PRICE_TYPE_MARKET
DEFAULT_PRICE = "0"
DEFAULT_TRIGGER_PRICE = "0"
DEFAULT_DISCLOSED_QUANTITY = "0"

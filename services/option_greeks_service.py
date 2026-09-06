"""
Option Greeks Service
Calculates option Greeks (Delta, Gamma, Theta, Vega, Rho) and Implied Volatility
for options across all supported exchanges (NFO, BFO, CDS, MCX)

Uses Black-76 model (opengreeks) - appropriate for options on futures/forwards
which is the correct model for Indian F&O markets (NFO, BFO, MCX, CDS).
opengreeks is a Rust reimplementation with byte-identical signatures to py_vollib.
"""

import re
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from utils.constants import CRYPTO_EXCHANGES
from utils.logging import get_logger

# opengreeks is lazy-loaded inside calculate_greeks() and check_opengreeks_availability().

logger = get_logger(__name__)

EST_TZ = ZoneInfo("America/New_York")
IST_TZ = ZoneInfo("Asia/Kolkata")

def get_exchange_timezone(exchange: str) -> ZoneInfo:
    """Resolve the timezone for a given exchange."""
    if exchange in ["NASDAQ", "NYSE", "AMEX", "OTCQX"]:
        return EST_TZ
    return IST_TZ

# Exchange-specific symbol mappings
NSE_INDEX_SYMBOLS = {
    "NIFTY",
    "BANKNIFTY",
    "FINNIFTY",
    "MIDCPNIFTY",
    "NIFTYNXT50",
    "NIFTYIT",
    "NIFTYPHARMA",
    "NIFTYBANK",
}

BSE_INDEX_SYMBOLS = {"SENSEX", "BANKEX", "SENSEX50"}

CURRENCY_SYMBOLS = {"USDINR", "EURINR", "GBPINR", "JPYINR"}

COMMODITY_SYMBOLS = {
    "GOLD",
    "GOLDM",
    "GOLDPETAL",
    "SILVER",
    "SILVERM",
    "SILVERMIC",
    "CRUDEOIL",
    "CRUDEOILM",
    "NATURALGAS",
    "COPPER",
    "ZINC",
    "LEAD",
    "ALUMINIUM",
    "NICKEL",
    "COTTONCANDY",
    "MENTHAOIL",
}

# Default interest rates by exchange (annualized %)
# Set to 0 - users should explicitly define interest rate if needed
DEFAULT_INTEREST_RATES = {
    "NFO": 0,  # NSE F&O
    "BFO": 0,  # BSE F&O
    "CDS": 0,  # Currency derivatives
    "MCX": 0,  # Commodities
}

MONTH_MAP = {
    "JAN": 1,
    "FEB": 2,
    "MAR": 3,
    "APR": 4,
    "MAY": 5,
    "JUN": 6,
    "JUL": 7,
    "AUG": 8,
    "SEP": 9,
    "OCT": 10,
    "NOV": 11,
    "DEC": 12,
}

# Expiry cut-off time (IST wall clock) per exchange. MCX is a default; the real
# cut-off varies by commodity, which is why callers can override it.
EXCHANGE_EXPIRY_TIMES = {
    "MCX": (23, 30),
    "CDS": (12, 30),
}

# NFO and BFO, and anything else that follows the equity-derivatives session.
DEFAULT_EXPIRY_TIME = (15, 30)


def get_exchange_expiry_time(
    exchange: str, custom_expiry_time: str | None = None
) -> tuple[int, int]:
    """
    Resolve the expiry cut-off time for an exchange.

    This is the single source of truth for how far into the expiry day an option
    still has time value. Both the greeks path and the option chain read it, so
    the two agree on time to expiry.

    Args:
        exchange: Exchange code (NFO, BFO, CDS, MCX, ...)
        custom_expiry_time: Optional override in "HH:MM" format

    Returns:
        Tuple of (hour, minute) in IST

    Raises:
        ValueError: If custom_expiry_time is malformed or out of range
    """
    if not custom_expiry_time:
        return EXCHANGE_EXPIRY_TIMES.get(exchange, DEFAULT_EXPIRY_TIME)

    time_parts = custom_expiry_time.split(":")
    if len(time_parts) != 2:
        raise ValueError(
            f"Invalid expiry_time format: {custom_expiry_time}. Use HH:MM format (e.g., '15:30', '19:00')"
        )

    try:
        expiry_hour = int(time_parts[0])
        expiry_minute = int(time_parts[1])
    except ValueError as e:
        raise ValueError(f"Failed to parse expiry_time '{custom_expiry_time}': {str(e)}") from e

    if not (0 <= expiry_hour <= 23) or not (0 <= expiry_minute <= 59):
        raise ValueError(
            f"Invalid expiry_time values: {custom_expiry_time}. Hour must be 0-23, minute must be 0-59"
        )

    return expiry_hour, expiry_minute


def get_expiry_datetime(
    expiry_date: str, exchange: str, custom_expiry_time: str | None = None
) -> datetime:
    """
    Build the localized expiry datetime from a DDMMMYY or YYMMDD expiry code.

    Args:
        expiry_date: Expiry in DDMMMYY format (e.g. "28NOV25") or YYMMDD format (e.g. "240816")
        exchange: Exchange code, used to pick the cut-off time
        custom_expiry_time: Optional override in "HH:MM" format

    Returns:
        Timezone-aware datetime
    """
    code = expiry_date.strip().upper()
    tz = get_exchange_timezone(exchange)
    
    # Try US YYMMDD format first
    us_match = re.fullmatch(r"(\d{2})(\d{2})(\d{2})", code)
    if us_match:
        year, month, day = us_match.groups()
        # Default US option close is 16:00 EST
        expiry_hour, expiry_minute = (16, 0)
        return datetime(
            int("20" + year),
            int(month),
            int(day),
            expiry_hour,
            expiry_minute,
            tzinfo=tz,
        )

    # Fallback to Indian format
    match = re.fullmatch(r"(\d{2})([A-Z]{3})(\d{2})", code)
    if not match:
        raise ValueError(f"Invalid expiry format: {expiry_date}. Expected YYMMDD or DDMMMYY")

    day, month_str, year = match.groups()
    if month_str not in MONTH_MAP:
        raise ValueError(f"Invalid month in expiry: {expiry_date}")

    expiry_hour, expiry_minute = get_exchange_expiry_time(exchange, custom_expiry_time)

    return datetime(
        int("20" + year),
        MONTH_MAP[month_str],
        int(day),
        expiry_hour,
        expiry_minute,
        tzinfo=tz,
    )


def check_opengreeks_availability():
    """Check if opengreeks library is available"""
    return True, None, None


def parse_option_symbol(
    symbol: str, exchange: str, custom_expiry_time: str | None = None
) -> tuple[str, datetime, float, str]:
    """
    Parse option symbol to extract underlying, expiry, strike, and option type.
    Supports both US OSI format (e.g. AAPL  240816C00200000) and legacy CE/PE formats.
    """
    symbol_upper = symbol.strip().upper()
    try:
        # 1. Try US OSI format first
        # Format: [Root: 1-6 chars][Expiry: 6 digits YYMMDD][Type: C/P][Strike: 8 digits]
        osi_match = re.match(r"^([A-Z\s]{1,6})(\d{6})([CP])(\d{8})$", symbol_upper)
        if osi_match:
            base_symbol_raw, expiry_str, opt_type_char, strike_str = osi_match.groups()
            base_symbol = base_symbol_raw.strip()
            
            year = expiry_str[0:2]
            month = expiry_str[2:4]
            day = expiry_str[4:6]
            
            # Default US option close is 16:00 EST
            expiry_hour, expiry_minute = (16, 0)
            
            expiry = datetime(
                int("20" + year),
                int(month),
                int(day),
                expiry_hour,
                expiry_minute,
            )
            opt_type = "CE" if opt_type_char == "C" else "PE"
            strike = float(strike_str) / 1000.0
            
            logger.info(
                f"Parsed US OSI symbol {symbol}: base={base_symbol}, expiry={expiry}, strike={strike}, type={opt_type}"
            )
            return base_symbol, expiry, strike, opt_type

        # 2. Fallback to legacy/Indian formats
        match = re.match(r"([A-Z]+)(\d{2})([A-Z]{3})(\d{2})([\d.]+)(CE|PE)", symbol_upper)
        if not match:
            raise ValueError(f"Invalid option symbol format: {symbol}")

        base_symbol, day, month_str, year, strike_str, opt_type = match.groups()

        if month_str not in MONTH_MAP:
            raise ValueError(f"Invalid month in option symbol: {symbol}")

        expiry_hour, expiry_minute = get_exchange_expiry_time(exchange, custom_expiry_time)

        expiry = datetime(
            int("20" + year),
            MONTH_MAP[month_str],
            int(day),
            expiry_hour,
            expiry_minute,
        )
        strike = float(strike_str)

        logger.info(
            f"Parsed legacy symbol {symbol}: base={base_symbol}, expiry={expiry}, strike={strike}, type={opt_type}"
        )

        return base_symbol, expiry, strike, opt_type.upper()

    except Exception as e:
        logger.exception(f"Error parsing option symbol {symbol}: {e}")
        raise ValueError(f"Failed to parse option symbol {symbol}: {str(e)}") from e


def get_underlying_exchange(base_symbol: str, options_exchange: str) -> str:
    """
    Determine the underlying exchange based on symbol and options exchange

    Returns:
        Exchange code for fetching underlying price
    """
    # NSE Index options
    if base_symbol in NSE_INDEX_SYMBOLS:
        return "NSE_INDEX"

    # BSE Index options
    if base_symbol in BSE_INDEX_SYMBOLS:
        return "BSE_INDEX"

    # Currency options
    if base_symbol in CURRENCY_SYMBOLS or options_exchange == "CDS":
        return "CDS"

    # Commodity options
    if base_symbol in COMMODITY_SYMBOLS or options_exchange == "MCX":
        return "MCX"

    # Crypto options — underlying is on the same exchange
    if options_exchange.upper() in CRYPTO_EXCHANGES:
        return options_exchange.upper()

    # Default to NSE for equity options
    return "NSE"


def _resolve_forward_price(
    base_symbol: str,
    options_exchange: str,
    underlying_exchange: str,
    expiry: datetime,
    api_key: str | None,
    synth_cache: dict | None = None,
) -> float | None:
    """
    Black-76 forward for an option's Greeks: the per-expiry SYNTHETIC FUTURE
    (ATM_strike + ATM_CE - ATM_PE, put-call parity) for every F&O underlying and
    expiry — index, stocks, MCX, CDS. Returns None to mean "fall back to spot"
    (e.g. the synthetic cannot be computed because ATM CE/PE quotes are missing).

    Single source of truth for the forward rule. Cached per
    (underlying, underlying_exchange, expiry) via synth_cache.
    """
    if synth_cache is None:
        synth_cache = {}
    expiry_code = expiry.strftime("%d%b%y").upper()  # DDMMMYY, e.g. 26JUN25
    key = (base_symbol, underlying_exchange, expiry_code)
    if key in synth_cache:
        return synth_cache[key]

    price = None
    try:
        from services.synthetic_future_service import calculate_synthetic_future

        ok, resp, _ = calculate_synthetic_future(
            base_symbol, underlying_exchange, expiry_code, api_key
        )
        if ok:
            price = resp.get("synthetic_future_price")
    except Exception as e:
        logger.warning(f"Synthetic future calc failed for {base_symbol} {expiry_code}: {e}")
    synth_cache[key] = price
    return price


def calculate_time_to_expiry(expiry: datetime) -> tuple[float, float]:
    """
    Calculate time to expiry in years (for the Black-76 model).

    The math library (opengreeks) expects time to expiry in YEARS.
    Also returns days for display purposes.

    Returns:
        Tuple of (time_in_years, time_in_days)
    """
    if expiry.tzinfo is None:
        # Determine likely timezone based on default close times of Indian market
        if (expiry.hour, expiry.minute) in [(15, 30), (12, 30), (23, 30)]:
            tz = IST_TZ
        else:
            tz = EST_TZ
        expiry_for_calc = expiry.replace(tzinfo=tz)
        current_time = datetime.now(tz)
    else:
        expiry_for_calc = expiry
        current_time = datetime.now(expiry.tzinfo)

    if expiry_for_calc < current_time:
        logger.warning(f"Option has already expired: {expiry_for_calc}")
        return 0.0, 0.0

    # Calculate time to expiry
    time_delta = expiry_for_calc - current_time
    days_to_expiry = time_delta.total_seconds() / (60 * 60 * 24)
    years_to_expiry = days_to_expiry / 365.0

    # Ensure minimum value to avoid numerical issues
    if years_to_expiry < 0.0001:  # Less than ~1 hour
        years_to_expiry = 0.0001
        days_to_expiry = years_to_expiry * 365.0
        logger.info("Very close to expiry - using minimum 0.0001 years")

    logger.info(f"Time to expiry: {days_to_expiry:.4f} days ({years_to_expiry:.6f} years)")

    return years_to_expiry, days_to_expiry


def _expired_option_greeks_response(
    option_symbol: str,
    exchange: str,
    base_symbol: str,
    expiry: datetime,
    strike: float,
    opt_type: str,
    spot_price: float,
    option_price: float,
    interest_rate: float | None,
) -> dict[str, Any]:
    """Return a stable batch response for expired option legs."""
    if opt_type == "CE":
        intrinsic_value = max(spot_price - strike, 0)
    else:
        intrinsic_value = max(strike - spot_price, 0)

    return {
        "status": "success",
        "symbol": option_symbol,
        "exchange": exchange,
        "underlying": base_symbol,
        "strike": round(strike, 2),
        "option_type": opt_type,
        "expiry_date": expiry.strftime("%d-%b-%Y"),
        "days_to_expiry": 0,
        "spot_price": round(spot_price, 2),
        "option_price": round(option_price, 2),
        "intrinsic_value": round(intrinsic_value, 2),
        "time_value": round(max(option_price - intrinsic_value, 0), 2),
        "interest_rate": round(interest_rate or 0, 2),
        "implied_volatility": 0,
        "greeks": {
            "delta": 0,
            "gamma": 0,
            "theta": 0,
            "vega": 0,
            "rho": 0,
        },
        "note": "Option has expired - Greeks are no longer applicable",
    }


def _is_expired_option_response(response: dict[str, Any]) -> bool:
    message = str(response.get("message", "")).lower()
    return "option has expired" in message


def calculate_chain_greeks(
    strikes: list[float],
    ce_prices: list[float | None],
    pe_prices: list[float | None],
    forward_price: float,
    time_to_expiry_years: float,
    interest_rate: float | None = None,
) -> tuple[list[dict[str, float] | None], list[dict[str, float] | None]]:
    """
    Compute IV and Greeks for an entire option chain in one pass using BSM.
    """
    count = len(strikes)
    if count == 0:
        return [], []

    rate_decimal = (interest_rate or 0) / 100.0

    def _side(prices: list[float | None], flag: str) -> list[dict[str, float] | None]:
        out = [None] * count
        for i in range(count):
            price = prices[i]
            if price is None or price <= 0:
                continue
            strike = strikes[i]
            if strike <= 0:
                continue

            # Intrinsic value
            if flag == "c":
                intrinsic = max(forward_price - strike, 0.0)
            else:
                intrinsic = max(strike - forward_price, 0.0)

            time_value = price - intrinsic
            if time_value <= 0 or (intrinsic > 0 and time_value < 0.01):
                out[i] = {
                    "iv": 0,
                    "delta": 1.0 if flag == "c" and intrinsic > 0 else (-1.0 if flag == "p" and intrinsic > 0 else 0.0),
                    "gamma": 0.0,
                    "theta": 0.0,
                    "vega": 0.0,
                }
                continue

            try:
                # Solve IV
                iv_val = bsm_iv(price, forward_price, strike, time_to_expiry_years, rate_decimal, flag)
                if iv_val > 0:
                    g = bsm_greeks(forward_price, strike, time_to_expiry_years, rate_decimal, iv_val, flag)
                    out[i] = {
                        "iv": round(iv_val * 100.0, 2),
                        "delta": round(g["delta"], 4),
                        "gamma": round(g["gamma"], 6),
                        "theta": round(g["theta"], 4),
                        "vega": round(g["vega"], 4),
                    }
                else:
                    out[i] = {
                        "iv": 0,
                        "delta": 1.0 if flag == "c" and intrinsic > 0 else (-1.0 if flag == "p" and intrinsic > 0 else 0.0),
                        "gamma": 0.0,
                        "theta": 0.0,
                        "vega": 0.0,
                    }
            except Exception:
                out[i] = {
                    "iv": 0,
                    "delta": 1.0 if flag == "c" and intrinsic > 0 else (-1.0 if flag == "p" and intrinsic > 0 else 0.0),
                    "gamma": 0.0,
                    "theta": 0.0,
                    "vega": 0.0,
                }
        return out

    return _side(ce_prices, "c"), _side(pe_prices, "p")


import math

def norm_cdf(x):
    """Cumulative standard normal distribution function (approximation)"""
    return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0

def norm_pdf(x):
    """Probability density function of standard normal distribution"""
    return math.exp(-0.5 * x**2) / math.sqrt(2.0 * math.pi)

def bsm_price(S, K, T, r, sigma, flag):
    """Calculate Black-Scholes-Merton option price"""
    if T <= 0:
        return max(S - K, 0.0) if flag == "c" else max(K - S, 0.0)
    if sigma <= 0:
        return max(S - K * math.exp(-r * T), 0.0) if flag == "c" else max(K * math.exp(-r * T) - S, 0.0)
        
    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    
    if flag == "c":
        return S * norm_cdf(d1) - K * math.exp(-r * T) * norm_cdf(d2)
    else:
        return K * math.exp(-r * T) * norm_cdf(-d2) - S * norm_cdf(-d1)

def bsm_vega(S, K, T, r, sigma):
    """Calculate standard Vega (derivative with respect to sigma)"""
    if T <= 0 or sigma <= 0:
        return 0.0
    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    return S * math.sqrt(T) * norm_pdf(d1)

def bsm_iv(price, S, K, T, r, flag):
    """Calculate Implied Volatility using Newton-Raphson method"""
    if T <= 0:
        return 0.0
        
    # Check intrinsic value
    intrinsic = max(S - K * math.exp(-r * T), 0.0) if flag == "c" else max(K * math.exp(-r * T) - S, 0.0)
    if price <= intrinsic:
        return 0.0
        
    # Initial guess
    sigma = 0.5
    for i in range(100):
        p = bsm_price(S, K, T, r, sigma, flag)
        diff = p - price
        if abs(diff) < 1e-6:
            return sigma
        v = bsm_vega(S, K, T, r, sigma)
        if abs(v) < 1e-4:
            # Shift search
            sigma += 0.01 if diff < 0 else -0.01
            continue
        dx = diff / v
        sigma -= dx
        if sigma <= 0:
            sigma = 0.5 * (sigma + dx)  # dampening step
            
    return max(sigma, 0.0)

def bsm_greeks(S, K, T, r, sigma, flag):
    """Calculate all option greeks using BSM model"""
    if T <= 0 or sigma <= 0:
        delta = 1.0 if flag == "c" else -1.0
        return {"delta": delta, "gamma": 0.0, "theta": 0.0, "vega": 0.0, "rho": 0.0}
        
    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    
    if flag == "c":
        delta = norm_cdf(d1)
        theta = - (S * norm_pdf(d1) * sigma) / (2.0 * math.sqrt(T)) - r * K * math.exp(-r * T) * norm_cdf(d2)
        rho = K * T * math.exp(-r * T) * norm_cdf(d2) / 100.0
    else:
        delta = norm_cdf(d1) - 1.0
        theta = - (S * norm_pdf(d1) * sigma) / (2.0 * math.sqrt(T)) + r * K * math.exp(-r * T) * norm_cdf(-d2)
        rho = -K * T * math.exp(-r * T) * norm_cdf(-d2) / 100.0
        
    gamma = norm_pdf(d1) / (S * sigma * math.sqrt(T))
    vega = S * math.sqrt(T) * norm_pdf(d1) / 100.0
    
    # theta to daily theta
    theta = theta / 365.0
    
    return {"delta": delta, "gamma": gamma, "theta": theta, "vega": vega, "rho": rho}


def calculate_greeks(
    option_symbol: str,
    exchange: str,
    spot_price: float,
    option_price: float,
    interest_rate: float = None,
    expiry_time: str = None,
    api_key: str = None,
) -> tuple[bool, dict[str, Any], int]:
    """
    Calculate Option Greeks using Black-Scholes-Merton model
    """
    try:
        # Parse option symbol
        base_symbol, expiry, strike, opt_type = parse_option_symbol(
            option_symbol, exchange, expiry_time
        )

        # Calculate time to expiry
        time_to_expiry_years, time_to_expiry_days = calculate_time_to_expiry(expiry)

        if time_to_expiry_years <= 0:
            return (
                False,
                {
                    "status": "error",
                    "message": f"Option has expired on {expiry.strftime('%d-%b-%Y')}",
                },
                400,
            )

        # Use default interest rate if not provided
        if interest_rate is None:
            interest_rate = DEFAULT_INTEREST_RATES.get(exchange, 0)

        # Convert interest rate from percentage to decimal
        interest_rate_decimal = interest_rate / 100.0

        # Validate inputs
        if spot_price <= 0 or option_price <= 0:
            return (
                False,
                {"status": "error", "message": "Spot price and option price must be positive"},
                400,
            )

        if strike <= 0:
            return False, {"status": "error", "message": "Strike price must be positive"}, 400

        # Set option flag ('c' for call, 'p' for put)
        flag = "c" if opt_type == "CE" else "p"

        # Calculate intrinsic value
        if opt_type == "CE":
            intrinsic_value = max(spot_price - strike, 0)
        else:  # PE
            intrinsic_value = max(strike - spot_price, 0)

        # Check deep ITM
        time_value = option_price - intrinsic_value
        if time_value <= 0 or (intrinsic_value > 0 and time_value < 0.01):
            logger.info("Deep ITM option with no time value - returning theoretical Greeks")
            response = {
                "status": "success",
                "symbol": option_symbol,
                "exchange": exchange,
                "underlying": base_symbol,
                "strike": round(strike, 2),
                "option_type": opt_type,
                "expiry_date": expiry.strftime("%d-%b-%Y"),
                "days_to_expiry": round(time_to_expiry_days, 4),
                "spot_price": round(spot_price, 2),
                "option_price": round(option_price, 2),
                "intrinsic_value": round(intrinsic_value, 2),
                "time_value": round(max(time_value, 0), 2),
                "interest_rate": round(interest_rate, 2),
                "implied_volatility": 0,
                "greeks": {
                    "delta": 1.0 if opt_type == "CE" else -1.0,
                    "gamma": 0.0,
                    "theta": 0.0,
                    "vega": 0.0,
                    "rho": 0.0,
                },
                "note": "Deep ITM option with no time value - theoretical Greeks returned",
            }
            return True, response, 200

        # Calculate IV
        implied_volatility_decimal = bsm_iv(
            option_price, spot_price, strike, time_to_expiry_years, interest_rate_decimal, flag
        )
        implied_volatility = implied_volatility_decimal * 100.0

        # Calculate Greeks
        greeks = bsm_greeks(
            spot_price, strike, time_to_expiry_years, interest_rate_decimal, implied_volatility_decimal, flag
        )

        response = {
            "status": "success",
            "symbol": option_symbol,
            "exchange": exchange,
            "underlying": base_symbol,
            "strike": round(strike, 2),
            "option_type": opt_type,
            "expiry_date": expiry.strftime("%d-%b-%Y"),
            "days_to_expiry": round(time_to_expiry_days, 4),
            "spot_price": round(spot_price, 2),
            "option_price": round(option_price, 2),
            "interest_rate": round(interest_rate, 2),
            "implied_volatility": round(implied_volatility, 2),
            "greeks": {
                "delta": round(greeks["delta"], 4),
                "gamma": round(greeks["gamma"], 6),
                "theta": round(greeks["theta"], 4),
                "vega": round(greeks["vega"], 4),
                "rho": round(greeks["rho"], 6),
            },
        }

        logger.info(f"Greeks calculated successfully for {option_symbol} using Black-Scholes-Merton model")
        return True, response, 200

    except ValueError as e:
        logger.error(f"Validation error in calculate_greeks: {e}")
        return False, {"status": "error", "message": str(e)}, 400

    except Exception as e:
        logger.exception(f"Unexpected error in calculate_greeks: {e}")
        return (
            False,
            {"status": "error", "message": f"Failed to calculate option Greeks: {str(e)}"},
            500,
        )


def get_option_greeks(
    option_symbol: str,
    exchange: str,
    interest_rate: float | None = None,
    forward_price: float | None = None,
    underlying_symbol: str | None = None,
    underlying_exchange: str | None = None,
    expiry_time: str | None = None,
    api_key: str | None = None,
) -> tuple[bool, dict[str, Any], int]:
    """
    Get option Greeks by fetching current market prices and calculating

    Args:
        option_symbol: Option symbol
        exchange: Exchange code (NFO, BFO, CDS, MCX)
        interest_rate: Optional interest rate (default from exchange mapping)
        forward_price: Optional custom forward/synthetic futures price. If provided, skips underlying fetch.
        underlying_symbol: Optional underlying symbol to use for spot price (e.g., NIFTY or NIFTY28NOV24FUT)
        underlying_exchange: Optional underlying exchange (e.g., NSE_INDEX or NFO)
        expiry_time: Optional custom expiry time in "HH:MM" format (e.g., "19:00" for MCX)
        api_key: API key for authentication

    Returns:
        Tuple of (success, response_dict, status_code)
    """
    try:
        # Import here to avoid circular dependency
        from services.quotes_service import get_quotes

        # Parse symbol to get underlying (if not provided)
        base_symbol, expiry, strike, opt_type = parse_option_symbol(
            option_symbol, exchange, expiry_time
        )

        # Determine the forward/futures price to use
        if forward_price:
            # User provided custom forward price (e.g., synthetic future)
            spot_price = forward_price
            logger.info(f"Using custom forward price: {forward_price}")
        else:
            # Fetch underlying price from broker
            # Use provided underlying symbol/exchange or derive from option symbol
            if underlying_symbol:
                spot_symbol = underlying_symbol
                logger.info(f"Using custom underlying symbol: {underlying_symbol}")
            else:
                spot_symbol = base_symbol

            if underlying_exchange:
                spot_exchange = underlying_exchange
                logger.info(f"Using custom underlying exchange: {underlying_exchange}")
            else:
                spot_exchange = get_underlying_exchange(base_symbol, exchange)

            # Black-76 forward = per-expiry synthetic future for all F&O; spot
            # fallback. Skipped when the caller supplied a custom underlying
            # (e.g. a FUT symbol).
            resolved_forward = None
            if not underlying_symbol or underlying_symbol == base_symbol:
                resolved_forward = _resolve_forward_price(
                    base_symbol, exchange, spot_exchange, expiry, api_key
                )

            if resolved_forward:
                spot_price = resolved_forward
                logger.info(
                    f"Using forward {resolved_forward} for {option_symbol}"
                )
                success = True
            else:
                # Fetch underlying spot price
                logger.info(f"Fetching spot price for {spot_symbol} from {spot_exchange}")
                success, spot_response, status_code = get_quotes(spot_symbol, spot_exchange, api_key)

                if not success:
                    return (
                        False,
                        {
                            "status": "error",
                            "message": f"Failed to fetch underlying price: {spot_response.get('message', 'Unknown error')}",
                        },
                        status_code,
                    )

                spot_price = spot_response.get("data", {}).get("ltp")
            if not spot_price:
                return False, {"status": "error", "message": "Underlying LTP not available"}, 404

        # Fetch option price
        logger.info(f"Fetching option price for {option_symbol} from {exchange}")
        success, option_response, status_code = get_quotes(option_symbol, exchange, api_key)

        if not success:
            return (
                False,
                {
                    "status": "error",
                    "message": f"Failed to fetch option price: {option_response.get('message', 'Unknown error')}",
                },
                status_code,
            )

        option_price = option_response.get("data", {}).get("ltp")
        if not option_price:
            return False, {"status": "error", "message": "Option LTP not available"}, 404

        # Calculate Greeks
        return calculate_greeks(
            option_symbol=option_symbol,
            exchange=exchange,
            spot_price=spot_price,
            option_price=option_price,
            interest_rate=interest_rate,
            expiry_time=expiry_time,
            api_key=api_key,
        )

    except Exception as e:
        logger.exception(f"Error in get_option_greeks: {e}")
        return False, {"status": "error", "message": f"Failed to get option Greeks: {str(e)}"}, 500


def get_multi_option_greeks(
    symbols: list,
    interest_rate: float | None = None,
    expiry_time: str | None = None,
    api_key: str | None = None,
) -> tuple[bool, dict[str, Any], int]:
    """
    Get option Greeks for multiple symbols in a single call.
    Optimized to fetch spot prices once per underlying and batch option prices
    via get_multiquotes(), minimizing broker API calls.

    Args:
        symbols: List of dicts with 'symbol', 'exchange', optional 'underlying_symbol', 'underlying_exchange'
        interest_rate: Optional common interest rate for all symbols
        expiry_time: Optional common expiry time for all symbols
        api_key: API key for authentication

    Returns:
        Tuple of (success, response_dict, status_code)
    """
    from services.quotes_service import get_multiquotes, get_quotes

    # Early return for empty symbols list
    if not symbols:
        return (
            True,
            {"status": "success", "data": [], "summary": {"total": 0, "success": 0, "failed": 0}},
            200,
        )

    results = []
    success_count = 0
    failed_count = 0

    # Step 1: Parse all symbols and group by underlying for spot price fetch
    parsed_symbols = {}  # symbol -> (base_symbol, expiry, strike, opt_type)
    spot_keys = {}  # (spot_symbol, spot_exchange) -> spot_price
    symbol_to_spot_key = {}  # symbol -> (spot_symbol, spot_exchange)
    symbol_forward = {}  # symbol -> Black-76 forward (synthetic future)
    synth_cache = {}  # (base, underlying_exchange, expiry_code) -> synthetic future

    for sym_req in symbols:
        symbol = sym_req.get("symbol")
        exchange = sym_req.get("exchange")
        try:
            base_symbol, expiry, strike, opt_type = parse_option_symbol(symbol, exchange, expiry_time)
            parsed_symbols[symbol] = (base_symbol, expiry, strike, opt_type)

            # Determine spot symbol/exchange for this option (also the fallback
            # if the synthetic future cannot be computed for an index weekly)
            passed_underlying = sym_req.get("underlying_symbol")
            spot_symbol = passed_underlying or base_symbol
            spot_exchange = sym_req.get("underlying_exchange") or get_underlying_exchange(base_symbol, exchange)
            spot_key = (spot_symbol, spot_exchange)
            spot_keys[spot_key] = None  # will be filled with price
            symbol_to_spot_key[symbol] = spot_key

            # Black-76 forward = per-expiry synthetic future for all F&O; spot
            # fallback. Skipped if the caller passed a custom underlying
            # (e.g. an explicit FUT symbol).
            if not passed_underlying or passed_underlying == base_symbol:
                forward = _resolve_forward_price(
                    base_symbol, exchange, spot_exchange, expiry, api_key, synth_cache
                )
                if forward:
                    symbol_forward[symbol] = forward
        except Exception as e:
            logger.warning(f"Failed to parse symbol {symbol}: {e}")
            failed_count += 1
            results.append({
                "status": "error",
                "symbol": symbol,
                "exchange": exchange,
                "message": f"Failed to parse option symbol: {str(e)}",
            })

    # Step 2: Fetch spot prices — one API call per unique underlying
    for spot_key in spot_keys:
        spot_symbol, spot_exchange = spot_key
        try:
            logger.info(f"Fetching spot price for {spot_symbol} from {spot_exchange}")
            success, spot_response, status_code = get_quotes(spot_symbol, spot_exchange, api_key)
            if success:
                spot_price = spot_response.get("data", {}).get("ltp")
                if spot_price:
                    spot_keys[spot_key] = spot_price
                else:
                    logger.warning(f"No LTP in spot response for {spot_symbol}")
            else:
                logger.warning(f"Failed to fetch spot for {spot_symbol}: {spot_response.get('message')}")
        except Exception as e:
            logger.warning(f"Error fetching spot for {spot_symbol}: {e}")

    # Step 3: Batch fetch all option prices via get_multiquotes()
    option_symbols_to_fetch = []
    for sym_req in symbols:
        symbol = sym_req.get("symbol")
        if symbol in parsed_symbols:  # only if parsing succeeded
            option_symbols_to_fetch.append({
                "symbol": symbol,
                "exchange": sym_req.get("exchange"),
            })

    option_prices = {}  # symbol -> ltp
    if option_symbols_to_fetch:
        logger.info(f"Batch fetching {len(option_symbols_to_fetch)} option prices via multiquotes")
        try:
            mq_success, mq_response, mq_status = get_multiquotes(
                symbols=option_symbols_to_fetch, api_key=api_key
            )
            if mq_success and "results" in mq_response:
                for result in mq_response["results"]:
                    sym = result.get("symbol")
                    if sym and "data" in result:
                        ltp = result["data"].get("ltp")
                        if ltp:
                            option_prices[sym] = ltp
        except Exception as e:
            logger.warning(f"Multiquotes fetch failed: {e}")

    # Step 4: Calculate Greeks for each symbol using fetched prices
    for sym_req in symbols:
        symbol = sym_req.get("symbol")
        exchange = sym_req.get("exchange")

        # Skip if already failed during parsing
        if symbol not in parsed_symbols:
            continue

        # Forward price: synthetic future for index weeklies, else spot.
        # Falls back to spot if the synthetic future could not be computed.
        spot_key = symbol_to_spot_key.get(symbol)
        spot_price = symbol_forward.get(symbol) or (spot_keys.get(spot_key) if spot_key else None)
        if not spot_price:
            failed_count += 1
            results.append({
                "status": "error",
                "symbol": symbol,
                "exchange": exchange,
                "message": f"Failed to fetch underlying price for {spot_key[0] if spot_key else 'unknown'}",
            })
            continue

        # Get option price
        option_price = option_prices.get(symbol)
        if not option_price:
            failed_count += 1
            results.append({
                "status": "error",
                "symbol": symbol,
                "exchange": exchange,
                "message": "Option LTP not available",
            })
            continue

        # Calculate Greeks (pure math, no API calls)
        try:
            calc_success, calc_response, calc_status = calculate_greeks(
                option_symbol=symbol,
                exchange=exchange,
                spot_price=spot_price,
                option_price=option_price,
                interest_rate=interest_rate,
                expiry_time=expiry_time,
                api_key=api_key,
            )
            if calc_success:
                success_count += 1
            else:
                if _is_expired_option_response(calc_response):
                    base_symbol, expiry, strike, opt_type = parsed_symbols[symbol]
                    calc_response = _expired_option_greeks_response(
                        option_symbol=symbol,
                        exchange=exchange,
                        base_symbol=base_symbol,
                        expiry=expiry,
                        strike=strike,
                        opt_type=opt_type,
                        spot_price=spot_price,
                        option_price=option_price,
                        interest_rate=interest_rate,
                    )
                    success_count += 1
                else:
                    failed_count += 1
                    calc_response.setdefault("symbol", symbol)
                    calc_response.setdefault("exchange", exchange)
            results.append(calc_response)
        except Exception as e:
            logger.exception(f"Error calculating Greeks for {symbol}: {e}")
            failed_count += 1
            results.append({
                "status": "error",
                "symbol": symbol,
                "exchange": exchange,
                "message": str(e),
            })

    # Sort results to maintain original order
    symbol_order = {sym["symbol"]: idx for idx, sym in enumerate(symbols)}
    results.sort(key=lambda x: symbol_order.get(x.get("symbol"), 999))

    response = {
        "status": "success" if failed_count == 0 else "partial" if success_count > 0 else "error",
        "data": results,
        "summary": {"total": len(symbols), "success": success_count, "failed": failed_count},
    }
    if failed_count > 0:
        messages = []
        for result in results:
            if result.get("status") == "error" and result.get("message"):
                message = result["message"]
                if message not in messages:
                    messages.append(message)
        if messages:
            if response["status"] == "error":
                response["message"] = (
                    f"All option Greeks calculations failed: {'; '.join(messages[:3])}"
                )
            else:
                response["message"] = (
                    f"{failed_count} option Greeks calculation(s) failed: "
                    f"{'; '.join(messages[:3])}"
                )

    logger.info(f"Multi Greeks completed: {success_count}/{len(symbols)} successful")

    # Return False only when ALL operations fail (status='error')
    # Return True for 'success' or 'partial' (at least some succeeded)
    is_success = response["status"] != "error"
    return is_success, response, 200

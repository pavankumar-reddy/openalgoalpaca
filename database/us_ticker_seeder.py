# database/us_ticker_seeder.py
import logging
from sqlalchemy.orm import Session
from database.symbol import SymToken

logger = logging.getLogger(__name__)

US_TICKERS = [
    # Top S&P 500 & Nasdaq 100 equities + popular ETFs
    {"symbol": "AAPL", "brsymbol": "AAPL", "name": "Apple Inc.", "exchange": "NASDAQ", "brexchange": "NASDAQ", "token": "AAPL", "lotsize": 1, "instrumenttype": "EQUITY", "tick_size": 0.01, "contract_value": 1.0},
    {"symbol": "MSFT", "brsymbol": "MSFT", "name": "Microsoft Corporation", "exchange": "NASDAQ", "brexchange": "NASDAQ", "token": "MSFT", "lotsize": 1, "instrumenttype": "EQUITY", "tick_size": 0.01, "contract_value": 1.0},
    {"symbol": "AMZN", "brsymbol": "AMZN", "name": "Amazon.com Inc.", "exchange": "NASDAQ", "brexchange": "NASDAQ", "token": "AMZN", "lotsize": 1, "instrumenttype": "EQUITY", "tick_size": 0.01, "contract_value": 1.0},
    {"symbol": "NVDA", "brsymbol": "NVDA", "name": "NVIDIA Corporation", "exchange": "NASDAQ", "brexchange": "NASDAQ", "token": "NVDA", "lotsize": 1, "instrumenttype": "EQUITY", "tick_size": 0.01, "contract_value": 1.0},
    {"symbol": "GOOGL", "brsymbol": "GOOGL", "name": "Alphabet Inc. Class A", "exchange": "NASDAQ", "brexchange": "NASDAQ", "token": "GOOGL", "lotsize": 1, "instrumenttype": "EQUITY", "tick_size": 0.01, "contract_value": 1.0},
    {"symbol": "GOOG", "brsymbol": "GOOG", "name": "Alphabet Inc. Class C", "exchange": "NASDAQ", "brexchange": "NASDAQ", "token": "GOOG", "lotsize": 1, "instrumenttype": "EQUITY", "tick_size": 0.01, "contract_value": 1.0},
    {"symbol": "META", "brsymbol": "META", "name": "Meta Platforms Inc.", "exchange": "NASDAQ", "brexchange": "NASDAQ", "token": "META", "lotsize": 1, "instrumenttype": "EQUITY", "tick_size": 0.01, "contract_value": 1.0},
    {"symbol": "TSLA", "brsymbol": "TSLA", "name": "Tesla Inc.", "exchange": "NASDAQ", "brexchange": "NASDAQ", "token": "TSLA", "lotsize": 1, "instrumenttype": "EQUITY", "tick_size": 0.01, "contract_value": 1.0},
    {"symbol": "AVGO", "brsymbol": "AVGO", "name": "Broadcom Inc.", "exchange": "NASDAQ", "brexchange": "NASDAQ", "token": "AVGO", "lotsize": 1, "instrumenttype": "EQUITY", "tick_size": 0.01, "contract_value": 1.0},
    {"symbol": "LLY", "brsymbol": "LLY", "name": "Eli Lilly & Co.", "exchange": "NYSE", "brexchange": "NYSE", "token": "LLY", "lotsize": 1, "instrumenttype": "EQUITY", "tick_size": 0.01, "contract_value": 1.0},
    {"symbol": "JPM", "brsymbol": "JPM", "name": "JPMorgan Chase & Co.", "exchange": "NYSE", "brexchange": "NYSE", "token": "JPM", "lotsize": 1, "instrumenttype": "EQUITY", "tick_size": 0.01, "contract_value": 1.0},
    {"symbol": "UNH", "brsymbol": "UNH", "name": "UnitedHealth Group Inc.", "exchange": "NYSE", "brexchange": "NYSE", "token": "UNH", "lotsize": 1, "instrumenttype": "EQUITY", "tick_size": 0.01, "contract_value": 1.0},
    {"symbol": "V", "brsymbol": "V", "name": "Visa Inc.", "exchange": "NYSE", "brexchange": "NYSE", "token": "V", "lotsize": 1, "instrumenttype": "EQUITY", "tick_size": 0.01, "contract_value": 1.0},
    {"symbol": "MA", "brsymbol": "MA", "name": "Mastercard Inc.", "exchange": "NYSE", "brexchange": "NYSE", "token": "MA", "lotsize": 1, "instrumenttype": "EQUITY", "tick_size": 0.01, "contract_value": 1.0},
    {"symbol": "XOM", "brsymbol": "XOM", "name": "Exxon Mobil Corp.", "exchange": "NYSE", "brexchange": "NYSE", "token": "XOM", "lotsize": 1, "instrumenttype": "EQUITY", "tick_size": 0.01, "contract_value": 1.0},
    {"symbol": "JNJ", "brsymbol": "JNJ", "name": "Johnson & Johnson", "exchange": "NYSE", "brexchange": "NYSE", "token": "JNJ", "lotsize": 1, "instrumenttype": "EQUITY", "tick_size": 0.01, "contract_value": 1.0},
    {"symbol": "PG", "brsymbol": "PG", "name": "Procter & Gamble Co.", "exchange": "NYSE", "brexchange": "NYSE", "token": "PG", "lotsize": 1, "instrumenttype": "EQUITY", "tick_size": 0.01, "contract_value": 1.0},
    {"symbol": "HD", "brsymbol": "HD", "name": "Home Depot Inc.", "exchange": "NYSE", "brexchange": "NYSE", "token": "HD", "lotsize": 1, "instrumenttype": "EQUITY", "tick_size": 0.01, "contract_value": 1.0},
    {"symbol": "COST", "brsymbol": "COST", "name": "Costco Wholesale Corp.", "exchange": "NASDAQ", "brexchange": "NASDAQ", "token": "COST", "lotsize": 1, "instrumenttype": "EQUITY", "tick_size": 0.01, "contract_value": 1.0},
    {"symbol": "NFLX", "brsymbol": "NFLX", "name": "Netflix Inc.", "exchange": "NASDAQ", "brexchange": "NASDAQ", "token": "NFLX", "lotsize": 1, "instrumenttype": "EQUITY", "tick_size": 0.01, "contract_value": 1.0},
    {"symbol": "AMD", "brsymbol": "AMD", "name": "Advanced Micro Devices Inc.", "exchange": "NASDAQ", "brexchange": "NASDAQ", "token": "AMD", "lotsize": 1, "instrumenttype": "EQUITY", "tick_size": 0.01, "contract_value": 1.0},
    {"symbol": "CRM", "brsymbol": "CRM", "name": "Salesforce Inc.", "exchange": "NYSE", "brexchange": "NYSE", "token": "CRM", "lotsize": 1, "instrumenttype": "EQUITY", "tick_size": 0.01, "contract_value": 1.0},
    {"symbol": "KO", "brsymbol": "KO", "name": "Coca-Cola Co.", "exchange": "NYSE", "brexchange": "NYSE", "token": "KO", "lotsize": 1, "instrumenttype": "EQUITY", "tick_size": 0.01, "contract_value": 1.0},
    {"symbol": "PEP", "brsymbol": "PEP", "name": "PepsiCo Inc.", "exchange": "NASDAQ", "brexchange": "NASDAQ", "token": "PEP", "lotsize": 1, "instrumenttype": "EQUITY", "tick_size": 0.01, "contract_value": 1.0},
    {"symbol": "ADBE", "brsymbol": "ADBE", "name": "Adobe Inc.", "exchange": "NASDAQ", "brexchange": "NASDAQ", "token": "ADBE", "lotsize": 1, "instrumenttype": "EQUITY", "tick_size": 0.01, "contract_value": 1.0},
    {"symbol": "DIS", "brsymbol": "DIS", "name": "Walt Disney Co.", "exchange": "NYSE", "brexchange": "NYSE", "token": "DIS", "lotsize": 1, "instrumenttype": "EQUITY", "tick_size": 0.01, "contract_value": 1.0},
    {"symbol": "WMT", "brsymbol": "WMT", "name": "Walmart Inc.", "exchange": "NYSE", "brexchange": "NYSE", "token": "WMT", "lotsize": 1, "instrumenttype": "EQUITY", "tick_size": 0.01, "contract_value": 1.0},
    {"symbol": "BAC", "brsymbol": "BAC", "name": "Bank of America Corp.", "exchange": "NYSE", "brexchange": "NYSE", "token": "BAC", "lotsize": 1, "instrumenttype": "EQUITY", "tick_size": 0.01, "contract_value": 1.0},
    {"symbol": "CSCO", "brsymbol": "CSCO", "name": "Cisco Systems Inc.", "exchange": "NASDAQ", "brexchange": "NASDAQ", "token": "CSCO", "lotsize": 1, "instrumenttype": "EQUITY", "tick_size": 0.01, "contract_value": 1.0},
    {"symbol": "QCOM", "brsymbol": "QCOM", "name": "QUALCOMM Inc.", "exchange": "NASDAQ", "brexchange": "NASDAQ", "token": "QCOM", "lotsize": 1, "instrumenttype": "EQUITY", "tick_size": 0.01, "contract_value": 1.0},
    {"symbol": "INTC", "brsymbol": "INTC", "name": "Intel Corp.", "exchange": "NASDAQ", "brexchange": "NASDAQ", "token": "INTC", "lotsize": 1, "instrumenttype": "EQUITY", "tick_size": 0.01, "contract_value": 1.0},
    {"symbol": "TXN", "brsymbol": "TXN", "name": "Texas Instruments Inc.", "exchange": "NASDAQ", "brexchange": "NASDAQ", "token": "TXN", "lotsize": 1, "instrumenttype": "EQUITY", "tick_size": 0.01, "contract_value": 1.0},
    {"symbol": "AMGN", "brsymbol": "AMGN", "name": "Amgen Inc.", "exchange": "NASDAQ", "brexchange": "NASDAQ", "token": "AMGN", "lotsize": 1, "instrumenttype": "EQUITY", "tick_size": 0.01, "contract_value": 1.0},
    {"symbol": "ISRG", "brsymbol": "ISRG", "name": "Intuitive Surgical Inc.", "exchange": "NASDAQ", "brexchange": "NASDAQ", "token": "ISRG", "lotsize": 1, "instrumenttype": "EQUITY", "tick_size": 0.01, "contract_value": 1.0},
    {"symbol": "NOW", "brsymbol": "NOW", "name": "ServiceNow Inc.", "exchange": "NYSE", "brexchange": "NYSE", "token": "NOW", "lotsize": 1, "instrumenttype": "EQUITY", "tick_size": 0.01, "contract_value": 1.0},
    {"symbol": "INTU", "brsymbol": "INTU", "name": "Intuit Inc.", "exchange": "NASDAQ", "brexchange": "NASDAQ", "token": "INTU", "lotsize": 1, "instrumenttype": "EQUITY", "tick_size": 0.01, "contract_value": 1.0},
    {"symbol": "SPY", "brsymbol": "SPY", "name": "SPDR S&P 500 ETF Trust", "exchange": "AMEX", "brexchange": "AMEX", "token": "SPY", "lotsize": 1, "instrumenttype": "EQUITY", "tick_size": 0.01, "contract_value": 1.0},
    {"symbol": "QQQ", "brsymbol": "QQQ", "name": "Invesco QQQ Trust Class 1", "exchange": "NASDAQ", "brexchange": "NASDAQ", "token": "QQQ", "lotsize": 1, "instrumenttype": "EQUITY", "tick_size": 0.01, "contract_value": 1.0},
    {"symbol": "IWM", "brsymbol": "IWM", "name": "iShares Russell 2000 ETF", "exchange": "NYSE", "brexchange": "NYSE", "token": "IWM", "lotsize": 1, "instrumenttype": "EQUITY", "tick_size": 0.01, "contract_value": 1.0},
    {"symbol": "DIA", "brsymbol": "DIA", "name": "SPDR Dow Jones Industrial Average ETF Trust", "exchange": "NYSE", "brexchange": "NYSE", "token": "DIA", "lotsize": 1, "instrumenttype": "EQUITY", "tick_size": 0.01, "contract_value": 1.0},
    {"symbol": "TQQQ", "brsymbol": "TQQQ", "name": "ProShares UltraPro QQQ (3x Long)", "exchange": "NASDAQ", "brexchange": "NASDAQ", "token": "TQQQ", "lotsize": 1, "instrumenttype": "EQUITY", "tick_size": 0.01, "contract_value": 1.0},
    {"symbol": "SQQQ", "brsymbol": "SQQQ", "name": "ProShares UltraPro Short QQQ (3x Short)", "exchange": "NASDAQ", "brexchange": "NASDAQ", "token": "SQQQ", "lotsize": 1, "instrumenttype": "EQUITY", "tick_size": 0.01, "contract_value": 1.0},
    {"symbol": "SPXL", "brsymbol": "SPXL", "name": "Direxion Daily S&P 500 Bull 3X Shares", "exchange": "NYSE", "brexchange": "NYSE", "token": "SPXL", "lotsize": 1, "instrumenttype": "EQUITY", "tick_size": 0.01, "contract_value": 1.0},
    {"symbol": "SPXS", "brsymbol": "SPXS", "name": "Direxion Daily S&P 500 Bear 3X Shares", "exchange": "NYSE", "brexchange": "NYSE", "token": "SPXS", "lotsize": 1, "instrumenttype": "EQUITY", "tick_size": 0.01, "contract_value": 1.0},
    {"symbol": "SOXL", "brsymbol": "SOXL", "name": "Direxion Daily Semiconductor Bull 3X Shares", "exchange": "NYSE", "brexchange": "NYSE", "token": "SOXL", "lotsize": 1, "instrumenttype": "EQUITY", "tick_size": 0.01, "contract_value": 1.0},
    {"symbol": "SOXS", "brsymbol": "SOXS", "name": "Direxion Daily Semiconductor Bear 3X Shares", "exchange": "NYSE", "brexchange": "NYSE", "token": "SOXS", "lotsize": 1, "instrumenttype": "EQUITY", "tick_size": 0.01, "contract_value": 1.0},
    # Cheap & High Performing Sector/Leveraged ETFs
    {"symbol": "LABU", "brsymbol": "LABU", "name": "Direxion Daily Biotech Bull 3X", "exchange": "NASDAQ", "brexchange": "NASDAQ", "token": "LABU", "lotsize": 1, "instrumenttype": "EQUITY", "tick_size": 0.01, "contract_value": 1.0},
    {"symbol": "SILJ", "brsymbol": "SILJ", "name": "ETFMG Junior Silver Miners ETF", "exchange": "AMEX", "brexchange": "AMEX", "token": "SILJ", "lotsize": 1, "instrumenttype": "EQUITY", "tick_size": 0.01, "contract_value": 1.0},
    {"symbol": "BITX", "brsymbol": "BITX", "name": "2X Bitcoin Strategy ETF", "exchange": "BATS", "brexchange": "BATS", "token": "BITX", "lotsize": 1, "instrumenttype": "EQUITY", "tick_size": 0.01, "contract_value": 1.0},
    {"symbol": "SCHD", "brsymbol": "SCHD", "name": "Schwab US Dividend Equity ETF", "exchange": "AMEX", "brexchange": "AMEX", "token": "SCHD", "lotsize": 1, "instrumenttype": "EQUITY", "tick_size": 0.01, "contract_value": 1.0},
    {"symbol": "JEPI", "brsymbol": "JEPI", "name": "JPMorgan Equity Premium Income ETF", "exchange": "AMEX", "brexchange": "AMEX", "token": "JEPI", "lotsize": 1, "instrumenttype": "EQUITY", "tick_size": 0.01, "contract_value": 1.0},
    {"symbol": "XLF", "brsymbol": "XLF", "name": "Financial Select Sector SPDR ETF", "exchange": "AMEX", "brexchange": "AMEX", "token": "XLF", "lotsize": 1, "instrumenttype": "EQUITY", "tick_size": 0.01, "contract_value": 1.0},
    {"symbol": "XLE", "brsymbol": "XLE", "name": "Energy Select Sector SPDR ETF", "exchange": "AMEX", "brexchange": "AMEX", "token": "XLE", "lotsize": 1, "instrumenttype": "EQUITY", "tick_size": 0.01, "contract_value": 1.0},
    {"symbol": "XBI", "brsymbol": "XBI", "name": "SPDR S&P Biotech ETF", "exchange": "AMEX", "brexchange": "AMEX", "token": "XBI", "lotsize": 1, "instrumenttype": "EQUITY", "tick_size": 0.01, "contract_value": 1.0},
    {"symbol": "ARKK", "brsymbol": "ARKK", "name": "ARK Innovation ETF", "exchange": "NYSE", "brexchange": "NYSE", "token": "ARKK", "lotsize": 1, "instrumenttype": "EQUITY", "tick_size": 0.01, "contract_value": 1.0},
    {"symbol": "SMH", "brsymbol": "SMH", "name": "VanEck Semiconductor ETF", "exchange": "NASDAQ", "brexchange": "NASDAQ", "token": "SMH", "lotsize": 1, "instrumenttype": "EQUITY", "tick_size": 0.01, "contract_value": 1.0},
    {"symbol": "VOO", "brsymbol": "VOO", "name": "Vanguard S&P 500 ETF", "exchange": "NYSE", "brexchange": "NYSE", "token": "VOO", "lotsize": 1, "instrumenttype": "EQUITY", "tick_size": 0.01, "contract_value": 1.0},
    {"symbol": "TECL", "brsymbol": "TECL", "name": "Direxion Daily Technology Bull 3X", "exchange": "NYSE", "brexchange": "NYSE", "token": "TECL", "lotsize": 1, "instrumenttype": "EQUITY", "tick_size": 0.01, "contract_value": 1.0},
    {"symbol": "PLTR", "brsymbol": "PLTR", "name": "Palantir Technologies Inc.", "exchange": "NASDAQ", "brexchange": "NASDAQ", "token": "PLTR", "lotsize": 1, "instrumenttype": "EQUITY", "tick_size": 0.01, "contract_value": 1.0},
    {"symbol": "SMCI", "brsymbol": "SMCI", "name": "Super Micro Computer Inc.", "exchange": "NASDAQ", "brexchange": "NASDAQ", "token": "SMCI", "lotsize": 1, "instrumenttype": "EQUITY", "tick_size": 0.01, "contract_value": 1.0},
]

def seed_us_tickers(session: Session):
    """Seed default US stock tickers if table is empty or missing any tickers"""
    try:
        logger.info(f"US Ticker Seeder: Checking/seeding {len(US_TICKERS)} popular US stock tickers...")
        added_count = 0
        for ticker in US_TICKERS:
            # Check if this symbol already exists
            existing = session.query(SymToken).filter_by(symbol=ticker["symbol"], exchange=ticker["exchange"]).first()
            if not existing:
                token = SymToken(
                    symbol=ticker["symbol"],
                    brsymbol=ticker["brsymbol"],
                    name=ticker["name"],
                    exchange=ticker["exchange"],
                    brexchange=ticker["brexchange"],
                    token=ticker["token"],
                    lotsize=ticker["lotsize"],
                    instrumenttype=ticker["instrumenttype"],
                    tick_size=ticker["tick_size"],
                    contract_value=ticker["contract_value"]
                )
                session.add(token)
                added_count += 1
        
        if added_count > 0:
            session.commit()
            logger.info(f"US Ticker Seeder: Successfully seeded {added_count} new tickers.")
        else:
            logger.info("US Ticker Seeder: All tickers already present in the database.")
    except Exception as e:
        session.rollback()
        logger.error(f"US Ticker Seeder: Error seeding US tickers: {e}")

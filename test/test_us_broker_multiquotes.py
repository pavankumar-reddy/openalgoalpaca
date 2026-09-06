from unittest.mock import MagicMock, patch
import pytest

from broker.alpaca.api.data import BrokerData as AlpacaData
from broker.robinhood.api.data import BrokerData as RobinhoodData
from broker.ibkr.api.data import BrokerData as IBKRData


def test_alpaca_get_multiquotes_dict_list():
    alpaca = AlpacaData(auth_token="test_token")
    symbols = [{"symbol": "SPXS", "exchange": "NYSE"}, {"symbol": "AAPL", "exchange": "NASDAQ"}]
    
    mock_quote = {"ask": 10.0, "bid": 9.9, "high": 10.5, "low": 9.8, "ltp": 10.0, "open": 9.9, "prev_close": 9.9, "volume": 100, "oi": 0}
    with patch.object(AlpacaData, "get_quotes", return_value=mock_quote):
        res = alpaca.get_multiquotes(symbols)
        assert len(res) == 2
        assert res[0] == {"symbol": "SPXS", "exchange": "NYSE", "data": mock_quote}
        assert res[1] == {"symbol": "AAPL", "exchange": "NASDAQ", "data": mock_quote}


def test_alpaca_get_multiquotes_string_list():
    alpaca = AlpacaData(auth_token="test_token")
    symbols = ["NYSE:SPXS", "AAPL"]
    
    mock_quote = {"ask": 10.0, "bid": 9.9, "high": 10.5, "low": 9.8, "ltp": 10.0, "open": 9.9, "prev_close": 9.9, "volume": 100, "oi": 0}
    with patch.object(AlpacaData, "get_quotes", return_value=mock_quote):
        res = alpaca.get_multiquotes(symbols)
        assert len(res) == 2
        assert res[0] == {"symbol": "SPXS", "exchange": "NYSE", "data": mock_quote}
        assert res[1] == {"symbol": "AAPL", "exchange": "NASDAQ", "data": mock_quote}


def test_robinhood_get_multiquotes_dict_list():
    rh = RobinhoodData(auth_token="test_token")
    symbols = [{"symbol": "SPXS", "exchange": "NYSE"}]
    mock_quote = {"ask": 10.0, "bid": 9.9, "high": 10.5, "low": 9.8, "ltp": 10.0, "open": 9.9, "prev_close": 9.9, "volume": 100, "oi": 0}
    with patch.object(RobinhoodData, "get_quotes", return_value=mock_quote):
        res = rh.get_multiquotes(symbols)
        assert len(res) == 1
        assert res[0] == {"symbol": "SPXS", "exchange": "NYSE", "data": mock_quote}


def test_ibkr_get_multiquotes_dict_list():
    ibkr = IBKRData(auth_token="test_token")
    symbols = [{"symbol": "SPXS", "exchange": "NYSE"}]
    mock_quote = {"ask": 10.0, "bid": 9.9, "high": 10.5, "low": 9.8, "ltp": 10.0, "open": 9.9, "prev_close": 9.9, "volume": 100, "oi": 0}
    with patch.object(IBKRData, "get_quotes", return_value=mock_quote):
        res = ibkr.get_multiquotes(symbols)
        assert len(res) == 1
        assert res[0] == {"symbol": "SPXS", "exchange": "NYSE", "data": mock_quote}

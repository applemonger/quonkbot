import pytest
from bot.stocks import QuoteException, get_stock_price


def test_get_stock_price():
    get_stock_price("MSFT")
    with pytest.raises(QuoteException):
        get_stock_price("FOOBARFOOBAR")

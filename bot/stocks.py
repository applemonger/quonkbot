import yfinance as yf
import os
import random

GENERATE_RANDOM_STOCK_VALUES = os.getenv("GENERATE_RANDOM_STOCK_VALUES")


class QuoteException(Exception):
    pass


def get_stock_price(ticker: str) -> float:
    if GENERATE_RANDOM_STOCK_VALUES:
        price = random.sample([100, 200], k=1)[0]
    else:
        yf_ticker = yf.Ticker(ticker)
        price = yf_ticker.info.get("currentPrice")
    if price is None:
        raise QuoteException(f"Unable to quote: ${ticker}")
    else:
        return price

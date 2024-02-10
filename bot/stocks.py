import yfinance as yf


class QuoteException(Exception):
    pass


def get_stock_price(ticker: str) -> float:
    yf_ticker = yf.Ticker(ticker)
    price = yf_ticker.info.get("currentPrice")
    if price is None:
        raise QuoteException(f"Unable to quote: ${ticker}")
    else:
        return price

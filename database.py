import duckdb
import os
from dotenv import load_dotenv
from typing import Iterator

load_dotenv()


class UserExistsException(Exception):
    pass


class InvalidSharesException(Exception):
    pass


class NotEnoughCashException(Exception):
    pass


class Holding:
    def __init__(self, ticker: str, shares: int):
        self.ticker = ticker
        self.shares = shares


class Database:
    PRECISION = 18
    SCALE = 6

    def __init__(self, path: str | None = None):
        self.db = duckdb.connect(path or os.getenv("DATABASE_PATH"))
        self.db.execute("CREATE TABLE IF NOT EXISTS MEMBERS (id BIGINT PRIMARY KEY);")
        self.db.execute(
            f"""
            CREATE TABLE IF NOT EXISTS CASH (
                id BIGINT PRIMARY KEY, 
                cash DECIMAL({self.PRECISION}, {self.SCALE})
            );
        """
        )
        self.db.execute(
            f"""
            CREATE TABLE IF NOT EXISTS HOLDINGS (
                id BIGINT, 
                ticker VARCHAR, 
                shares INTEGER, 
                price DECIMAL({self.PRECISION}, {self.SCALE})
            );
        """
        )

    def trunc(self, x) -> float:
        return round(float(x), self.SCALE)

    def register_user(self, member_id: int) -> bool:
        try:
            self.db.execute("INSERT INTO MEMBERS VALUES (?)", [member_id])
            self.db.execute("INSERT INTO CASH VALUES (?, ?)", [member_id, 10000])
            return True
        except duckdb.ConstraintException:
            raise UserExistsException("User is already registered.")

    def user_exists(self, member_id: int) -> bool:
        query = "SELECT COUNT(*) FROM MEMBERS WHERE id = ?"
        result = self.db.execute(query, [member_id]).fetchone()
        user_exists = int(result[0]) == 1
        return user_exists

    def get_cash(self, member_id: int) -> float:
        query = "SELECT cash FROM CASH WHERE id = ?"
        result = self.db.execute(query, [member_id]).fetchone()
        return self.trunc(result[0])

    def add_cash(self, member_id: int, delta: float):
        delta = self.trunc(delta)
        cash = self.get_cash(member_id) + delta
        self.db.execute("UPDATE CASH SET cash = ? WHERE id = ?", [cash, member_id])

    def get_shares(self, member_id: int, ticker: str) -> int:
        query = """
            SELECT SUM(shares)
            FROM HOLDINGS 
            WHERE id = ? AND ticker = ?
        """
        result = self.db.execute(query, [member_id, ticker]).fetchone()
        if result[0] is None:
            return 0
        else:
            return int(result[0])

    def get_holdings(self, member_id: int) -> Iterator[Holding]:
        query = """
            SELECT
                ticker,
                SUM(shares) AS shares,
            FROM HOLDINGS
            WHERE id = ?
            GROUP BY ticker
            ORDER BY ticker
        """
        holdings = self.db.execute(query, [member_id]).fetchall()
        for holding in holdings:
            yield Holding(holding[0], int(holding[1]))

    def add_holding(self, member_id: int, ticker: str, delta_shares: int, price: float):
        query = "INSERT INTO HOLDINGS VALUES (?, ?, ?, ?)"
        self.db.execute(query, [member_id, ticker, delta_shares, price])

    def get_profit(self, member_id: int, ticker: str, price: float):
        query = """
            SELECT SUM(shares * ABS(price - ?))
            FROM HOLDINGS
            WHERE id = ? AND ticker = ?
            GROUP BY id, ticker
        """
        result = self.db.execute(query, [price, member_id, ticker]).fetchone()
        if result is None:
            return 0
        else:
            return self.trunc(result[0])

    def get_value(self, member_id: int, ticker: str, price: float):
        query = """
            SELECT SUM(shares * (price + ABS(price - ?)))
            FROM HOLDINGS
            WHERE id = ? AND ticker = ?
            GROUP BY id, ticker
        """
        result = self.db.execute(query, [price, member_id, ticker]).fetchone()
        return self.trunc(result[0])

    def buy_stock(self, member_id: int, ticker: str, shares: int, price: float):
        # Reject attempts to buy zero or negative shares.
        if shares <= 0:
            raise InvalidSharesException("You cannot buy zero or negative shares.")
        # Get current cash on hand
        cash = self.get_cash(member_id)
        # Reject attempts to buy more than they have cash for
        if shares * price > cash:
            limit = int(cash / price)
            raise NotEnoughCashException(
                f"You only have enough to buy {limit} shares of ${ticker}."
            )
        else:
            # Otherwise, they have enough cash. Convert the cash to shares.
            cost = shares * price
            self.add_cash(member_id, cost * -1)
            self.add_holding(member_id, ticker, shares, price)

    def sell_stock(self, member_id: int, ticker: str, shares: int, price: float):
        # Reject attempts to buy zero or negative shares.
        if shares <= 0:
            raise InvalidSharesException("You cannot sell zero or negative shares")
        # Get current number of shares.
        current_holding = self.get_shares(member_id, ticker)
        # Reject attempts to sell more shares than they own.
        if shares > current_holding:
            raise InvalidSharesException("You cannot sell more shares than you own.")
        else:
            # Otherwise, they have enough shares. Convert shares to cash
            cash = shares * price
            self.add_cash(member_id, cash)
            self.add_holding(member_id, ticker, -shares, price)
            if self.get_shares(member_id, ticker) == 0:
                self.delete_holdings(member_id, ticker)

    def delete_holdings(self, member_id: int, ticker: str):
        query = "DELETE FROM HOLDINGS WHERE id = ? AND ticker = ?"
        self.db.execute(query, [member_id, ticker])

    def clear(self):
        self.db.execute("DROP TABLE MEMBERS;")
        self.db.execute("DROP TABLE CASH;")
        self.db.execute("DROP TABLE HOLDINGS;")

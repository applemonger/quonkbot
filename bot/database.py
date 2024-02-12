import duckdb
import os
from typing import Iterator


class UserExistsException(Exception):
    pass


class UserDoesNotExistException(Exception):
    pass


class NotEnoughCashException(Exception):
    pass


class InvalidSharesException(Exception):
    pass


class Holding:
    def __init__(self, db: "Database", member_id: int, ticker: str):
        self.db = db
        self.member_id = member_id
        self.ticker = ticker

    @property
    def shares(self):
        query = """
            SELECT shares
            FROM HOLDINGS
            WHERE id = ? AND ticker = ?
        """
        result = self.db.db.execute(query, [self.member_id, self.ticker]).fetchone()
        return int(result[0])

    @property
    def price(self):
        query = """
            SELECT price
            FROM HOLDINGS
            WHERE id = ? AND ticker = ?
        """
        result = self.db.db.execute(query, [self.member_id, self.ticker]).fetchone()
        return self.db.trunc(result[0])

    @property
    def value(self):
        query = """
            SELECT value
            FROM HOLDINGS
            WHERE id = ? AND ticker = ?
        """
        result = self.db.db.execute(query, [self.member_id, self.ticker]).fetchone()
        return self.db.trunc(result[0])


class Leader:
    def __init__(self, member_id: int, value: float):
        self.member_id = member_id
        self.value = value


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
                price DECIMAL({self.PRECISION}, {self.SCALE}),
                value DECIMAL({self.PRECISION}, {self.SCALE})
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

    def validate_user(self, member_id: int):
        if not self.user_exists(member_id):
            raise UserDoesNotExistException("User does not exist!")

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
            SELECT id, ticker
            FROM HOLDINGS
            WHERE id = ?
            ORDER BY ticker
        """
        holdings = self.db.execute(query, [member_id]).fetchall()
        for holding in holdings:
            yield Holding(
                db=self,
                member_id=member_id,
                ticker=holding[1],
            )

    def get_holding(self, member_id: int, ticker: str) -> Holding:
        return Holding(db=self, member_id=member_id, ticker=ticker)

    def observe_price(self, member_id: int, ticker: str, price: float):
        """
        Observation of price changes (always increases) the value of Quonks. If the
        observed price is higher than the last observed price, then the Quonks were
        long, and that value is accumulated. If the observed price is lower than the
        last observed price, then the Quonks were short, and the short value is
        accumulated.
        """
        query = """
            UPDATE HOLDINGS
            SET value = value + (shares * ABS(price - ?)), price = ?
            WHERE id = ? AND ticker = ?
        """
        self.db.execute(query, [price, price, member_id, ticker])

    def buy_quonks(self, member_id: int, ticker: str, shares: int, price: float):
        # Get current cash on hand
        cash = self.get_cash(member_id)
        # Reject attempts to buy more than they have cash for
        if shares * price > cash:
            limit = int(cash / price)
            if limit > 0:
                raise NotEnoughCashException(
                    f"You only have enough to buy {limit} shares of ${ticker}."
                )
            else:
                raise NotEnoughCashException(
                    f"You do not have enough cash to buy any shares of ${ticker}"
                )
        else:
            # Otherwise, they have enough cash. Convert the cash to shares.
            cost = shares * price
            self.add_cash(member_id, cost * -1)
            self.observe_price(member_id, ticker, price)
            if self.get_shares(member_id, ticker) == 0:
                query = "INSERT INTO HOLDINGS VALUES (?, ?, ?, ?, ?)"
                value = shares * price
                self.db.execute(query, [member_id, ticker, shares, price, value])
            else:
                query = """
                    UPDATE HOLDINGS
                    SET shares = shares + ?, value = value + (? * price)
                    WHERE id = ? AND ticker = ?
                """
                self.db.execute(query, [shares, shares, member_id, ticker])

    def sell_quonks(
        self, member_id: int, ticker: str, shares: int, price: float
    ) -> float:
        # Get current number of shares.
        current_holding = self.get_shares(member_id, ticker)
        # Reject attempts to sell more shares than they own.
        if shares > current_holding:
            raise InvalidSharesException("You cannot sell more shares than you own.")
        else:
            # Otherwise, they have enough shares. Convert shares to cash
            # Observe the selling price
            self.observe_price(member_id, ticker, price)
            query = """
                SELECT value / shares
                FROM HOLDINGS
                WHERE id = ? AND ticker = ?
            """
            result = self.db.execute(query, [member_id, ticker]).fetchone()
            quonk_price = self.trunc(result[0])
            quonk_value = quonk_price * shares
            self.add_cash(member_id, quonk_value)
            query = """
                UPDATE HOLDINGS
                SET shares = shares - ?, value = value - ?
                WHERE id = ? AND ticker = ?
            """
            self.db.execute(query, [shares, quonk_value, member_id, ticker])
            if self.get_shares(member_id, ticker) == 0:
                self.delete_holdings(member_id, ticker)
            return quonk_price

    def delete_holdings(self, member_id: int, ticker: str):
        query = "DELETE FROM HOLDINGS WHERE id = ? AND ticker = ?"
        self.db.execute(query, [member_id, ticker])

    def leaderboard(self):
        query = """
            SELECT a.id, SUM(a.value), SUM(b.cash)
            FROM HOLDINGS a
            LEFT JOIN CASH b ON a.id = b.id
            GROUP BY a.id
            ORDER BY SUM(a.value) DESC
            LIMIT 10
        """
        for leader in self.db.execute(query).fetchall():
            yield Leader(
                member_id=leader[0], value=self.trunc(leader[1]) + self.trunc(leader[2])
            )

    def clear(self):
        self.db.execute("DROP TABLE MEMBERS;")
        self.db.execute("DROP TABLE CASH;")
        self.db.execute("DROP TABLE HOLDINGS;")

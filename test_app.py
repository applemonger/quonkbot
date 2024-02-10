import pytest
from database import (
    Database,
    InvalidSharesException,
    NotEnoughCashException,
    UserExistsException,
)

EPSILON = 1e-10


def eq(a, b):
    return (a >= b - EPSILON) and (a <= b + EPSILON)


@pytest.fixture()
def db():
    db = Database("test.db")
    yield db
    db.clear()


class TestDatabase:
    def test_register_user(self, db: Database):
        # Registration succeeds
        assert db.register_user(0)
        # Registration fails
        with pytest.raises(UserExistsException):
            db.register_user(0)

    def test_user_exists(self, db: Database):
        assert not db.user_exists(0)
        db.register_user(0)
        assert db.user_exists(0)

    def test_get_cash(self, db: Database):
        db.register_user(0)
        cash = db.get_cash(0)
        assert cash >= 10000 and cash < 10000 + EPSILON

    def test_add_cash(self, db: Database):
        db.register_user(0)
        # Add a dollar
        db.add_cash(0, 1)
        assert eq(db.get_cash(0), 10001)
        # Add a dollar, but the 09 at the end gets chopped off
        db.add_cash(0, 1.00000009)
        assert eq(db.get_cash(0), 10002)
        # Subtract 10000 dollars
        db.add_cash(0, -10000)
        assert eq(db.get_cash(0), 2)

    def test_get_shares(self, db: Database):
        db.register_user(0)
        assert db.get_shares(0, "ABC") == 0
        db.add_holding(0, "ABC", 10, 10)
        assert db.get_shares(0, "ABC") == 10

    def test_buy_stock(self, db: Database):
        db.register_user(0)
        db.buy_stock(0, "ABC", 5, 1000)
        assert db.get_cash(0) == 5000
        assert db.get_shares(0, "ABC") == 5
        with pytest.raises(NotEnoughCashException):
            assert db.buy_stock(0, "ABC", 10000, 10000)
        with pytest.raises(InvalidSharesException):
            assert db.buy_stock(0, "ABC", -1, 1000)

    def test_sell_stock(self, db: Database):
        db.register_user(0)
        with pytest.raises(InvalidSharesException):
            assert db.sell_stock(0, "ABC", 10, 10)
        with pytest.raises(InvalidSharesException):
            assert db.sell_stock(0, "ABC", -10, 10)
        db.buy_stock(0, "ABC", 5, 1000)
        with pytest.raises(InvalidSharesException):
            assert db.sell_stock(0, "ABC", 6, 1000)
        db.sell_stock(0, "ABC", 3, 1200)
        assert db.get_shares(0, "ABC") == 2
        db.sell_stock(0, "ABC", 2, 1500)
        assert db.get_shares(0, "ABC") == 0

    def test_delete_holdings(self, db: Database):
        db.register_user(0)
        db.buy_stock(0, "ABC", 10, 10)
        assert db.get_shares(0, "ABC") == 10
        db.delete_holdings(0, "ABC")
        assert db.get_shares(0, "ABC") == 0

    def test_get_profit(self, db: Database):
        db.register_user(0)
        db.buy_stock(0, "ABC", 10, 10)
        assert db.get_profit(0, "ABC", 10) == 0
        assert db.get_profit(0, "ABC", 20) == 100
        db.buy_stock(0, "ABC", 10, 20)
        assert db.get_profit(0, "ABC", 10) == 100  # 10 shares have been shorted
        assert db.get_profit(0, "ABC", 20) == 100
        assert db.get_profit(0, "ABC", 5) == 5 * 10 + 15 * 10  # 20 shares shorted
        db.sell_stock(0, "ABC", 10, 20)
        assert db.get_profit(0, "ABC", 10) == 0
        assert db.get_profit(0, "ABC", 20) == 100
        db.sell_stock(0, "ABC", 10, 30)
        assert db.get_profit(0, "ABC", 10) == 0
        assert db.get_profit(0, "ABC", 20) == 0

    def test_get_value(self, db: Database):
        db.register_user(0)
        db.buy_stock(0, "ABC", 10, 10)
        assert db.get_value(0, "ABC", 10) == 100
        assert db.get_value(0, "ABC", 20) == 200
        assert db.get_value(0, "ABC", 0) == 200  # Shorted
        db.buy_stock(0, "ABC", 10, 20)
        assert db.get_value(0, "ABC", 10) == 10 * 10 + 30 * 10  # Shorted
        assert db.get_value(0, "ABC", 5) == 15 * 10 + 35 * 10  # Shorted
        assert db.get_value(0, "ABC", 30) == 30 * 20
        db.sell_stock(0, "ABC", 10, 15)
        assert db.get_value(0, "ABC", 20) == 10 * 20 + 10 * 20 - 10 * 20

    def test_get_holdings(self, db: Database):
        db.register_user(0)
        db.buy_stock(0, "XYZ", 10, 10)
        db.buy_stock(0, "ABC", 10, 10)
        holdings = db.get_holdings(0)
        assert next(holdings).ticker == "ABC"
        assert next(holdings).ticker == "XYZ"

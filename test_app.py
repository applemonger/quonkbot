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
        db.add_stock(0, "ABC", 10, 10)
        assert db.get_shares(0, "ABC") == 10

    def test_holding_exists(self, db: Database):
        db.register_user(0)
        db.add_stock(0, "ABC", 10, 10)
        assert db.holding_exists(0, "ABC")
        assert not db.holding_exists(0, "XYZ")

    def test_get_value(self, db: Database):
        db.register_user(0)
        db.add_stock(0, "ABC", 10, 10)
        assert db.get_value(0, "ABC") == 10
        assert db.get_value(0, "XYZ") == 0
        db.add_stock(0, "ABC", 10, 5)
        assert db.get_value(0, "ABC") == 5

    def test_add_stock(self, db: Database):
        db.register_user(0)
        db.add_stock(0, "ABC", 10, 10)
        result = db.db.execute(
            "SELECT id, ticker, shares, value FROM HOLDINGS WHERE id = 0 AND ticker = 'ABC'"
        ).fetchone()
        assert result[2] == 10
        assert result[3] == 10
        db.add_stock(0, "ABC", 10, 5)
        result = db.db.execute(
            "SELECT id, ticker, shares, value FROM HOLDINGS WHERE id = 0 AND ticker = 'ABC'"
        ).fetchone()
        assert result[2] == 20
        assert result[3] == 5

    def test_buy_stock(self, db: Database):
        db.register_user(0)
        db.buy_stock(0, "ABC", 5, 1000)
        assert db.get_cash(0) == 5000
        assert db.get_shares(0, "ABC") == 5
        assert db.get_value(0, "ABC") == 1000
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
        assert db.get_value(0, "ABC") == 1200
        db.sell_stock(0, "ABC", 2, 1500)
        assert db.get_shares(0, "ABC") == 0
        assert db.get_value(0, "ABC") == 0
        assert not db.holding_exists(0, "ABC")

import pytest
from bot.database import (
    Database,
    InvalidSharesException,
    NotEnoughCashException,
    UserDoesNotExistException,
    UserExistsException,
)

EPSILON = 1e-10


def eq(a, b):
    return (a >= b - EPSILON) and (a <= b + EPSILON)


@pytest.fixture()
def db():
    db = Database("db/test.db")
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

    def test_validate_user(self, db: Database):
        with pytest.raises(UserDoesNotExistException):
            db.validate_user(0)
        db.register_user(0)
        db.validate_user(0)

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
        db.buy_quonks(0, "ABC", 10, 10)
        assert db.get_shares(0, "ABC") == 10

    def test_get_holding(self, db: Database):
        db.register_user(0)
        db.buy_quonks(0, "ABC", 10, 10)
        holding = db.get_holding(0, "ABC")
        assert holding.ticker == "ABC"
        assert holding.price == 10
        assert holding.shares == 10
        assert holding.value == 100

    def test_get_holdings(self, db: Database):
        db.register_user(0)
        db.buy_quonks(0, "XYZ", 10, 10)
        db.buy_quonks(0, "ABC", 10, 10)
        holdings = db.get_holdings(0)
        assert next(holdings).ticker == "ABC"
        assert next(holdings).ticker == "XYZ"

    def test_observe_price(self, db: Database):
        db.register_user(0)
        db.buy_quonks(0, "ABC", 10, 10)
        holding = db.get_holding(0, "ABC")
        assert holding.value == 100  # 10 x 10
        db.observe_price(0, "ABC", 20)
        assert holding.value == 200  # 100 + (10 x +10)
        db.observe_price(0, "ABC", 10)
        assert holding.value == 300  # 200 + (10 x abs(-10))

    def test_buy_quonks(self, db: Database):
        db.register_user(0)
        db.buy_quonks(0, "ABC", 5, 1000)
        assert db.get_cash(0) == 5000
        assert db.get_shares(0, "ABC") == 5
        with pytest.raises(NotEnoughCashException):
            assert db.buy_quonks(0, "ABC", 10000, 10000)

    def test_sell_quonks(self, db: Database):
        db.register_user(0)
        assert db.get_cash(0) == 10000
        with pytest.raises(InvalidSharesException):
            db.sell_quonks(0, "ABC", 5, 1000)
        db.buy_quonks(0, "ABC", 5, 1000)
        assert db.get_cash(0) == 5000
        db.sell_quonks(0, "ABC", 3, 1200)
        assert db.get_cash(0) == 5000 + 3 * 1200
        assert db.get_shares(0, "ABC") == 2
        db.sell_quonks(0, "ABC", 2, 800)
        assert db.get_cash(0) == 5000 + 3 * 1200 + 2 * 1600
        assert db.get_shares(0, "ABC") == 0

    def test_delete_holdings(self, db: Database):
        db.register_user(0)
        db.buy_quonks(0, "ABC", 10, 10)
        assert db.get_shares(0, "ABC") == 10
        db.delete_holdings(0, "ABC")
        assert db.get_shares(0, "ABC") == 0

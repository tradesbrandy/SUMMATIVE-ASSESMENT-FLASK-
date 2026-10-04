import pytest

from app import create_app
from app.models import db


@pytest.fixture
def app():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


OFF_PRODUCT = {
    "barcode": "3017620422003",
    "name": "Nutella",
    "brand": "Ferrero",
    "category": "Spreads",
    "quantity": "400 g",
    "ingredients": "Sugar, palm oil, hazelnuts",
    "image_url": "http://img/x.jpg",
}

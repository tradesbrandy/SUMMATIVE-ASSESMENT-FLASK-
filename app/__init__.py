from flask import Flask, jsonify

from .models import db
from .routes import bp


def create_app(config=None):
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///inventory.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    if config:
        app.config.update(config)
    db.init_app(app)
    app.register_blueprint(bp)

    @app.get("/")
    def index():
        return jsonify({
            "service": "Inventory Admin Portal API",
            "endpoints": {
                "health": "GET /api/health",
                "list_items": "GET /api/items",
                "view_item": "GET /api/items/<id>",
                "create_item": "POST /api/items",
                "edit_item": "PATCH /api/items/<id>",
                "delete_item": "DELETE /api/items/<id>",
                "lookup_barcode": "GET /api/lookup/barcode/<barcode>",
                "lookup_name": "GET /api/lookup/search?name=<name>",
            },
        })

    with app.app_context():
        db.create_all()
    return app

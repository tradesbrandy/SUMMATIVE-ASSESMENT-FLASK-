from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Item(db.Model):
    __tablename__ = "items"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    barcode = db.Column(db.String(32), unique=True, nullable=True, index=True)
    price = db.Column(db.Float, nullable=False, default=0.0)
    quantity = db.Column(db.Integer, nullable=False, default=0)
    brand = db.Column(db.String(200), default="")
    category = db.Column(db.String(200), default="")
    ingredients = db.Column(db.Text, default="")
    image_url = db.Column(db.String(500), default="")

    FIELDS = (
        "name", "barcode", "price", "quantity",
        "brand", "category", "ingredients", "image_url",
    )

    def to_dict(self):
        data = {"id": self.id}
        for f in self.FIELDS:
            data[f] = getattr(self, f)
        return data

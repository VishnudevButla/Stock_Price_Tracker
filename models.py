from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer,autoincrement=True, nullable = False, primary_key=True)
    username = db.Column(db.String(256), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(512), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    saved_lists = db.relationship("SavedList", backref='owner', lazy=True)
    def __repr__(self):
        return f"<User {self.username}>"

class SavedList(db.Model):
    __tablename__ = 'saved_lists'

    id = db.Column(db.Integer, primary_key = True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable = False)
    name = db.Column(db.String(80), nullable = False)
    created_at = db.Column(db.DateTime, default = datetime.utcnow)
    items = db.relationship("SavedListItem", backref = 'list', lazy = True)
    def __repr__(self):
        return f"<SavedList {self.name}>"

class SavedListItem(db.Model):
    __tablename__ = 'saved_list_items'

    id = db.Column(db.Integer, primary_key = True)
    saved_list_id = db.Column(db.Integer, db.ForeignKey("saved_lists.id"),nullable = False)
    ticker = db.Column(db.String(10), nullable = False)
    added_at = db.Column(db.DateTime, default = datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("saved_list_id", "ticker", name = "unique_list_ticker"),
    )

    def __repr__(self):
        return f"<SavedListItem {self.ticker} in list {self.saved_list_id}>"

class PriceHistory(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    date = db.Column(db.Date, nullable=False)
    stock_id = db.Column(db.Integer, db.ForeignKey("stocks.id"), nullable = False)
    open_price = db.Column(db.Float, nullable = False)
    high_price = db.Column(db.Float)
    low_price = db.Column(db.Float)
    close_price = db.Column(db.Float, nullable = False)
    volume = db.Column(db.BigInteger)
    __table_args__ = (
        db.UniqueConstraint("stock_id", "date", name = "unique_stock_date"),
    )
    def __repr__(self):
        return f"<PriceHistory {self.stock_id} on {self.date}>"

class StockDetails(db.Model):
    __tablename__ = "stocks"

    id = db.Column(db.Integer, primary_key = True)
    ticker = db.Column(db.String(10), nullable = False)
    company_name = db.Column(db.String(250))
    current_price = db.Column(db.Float)
    open_price = db.Column(db.Float)
    high_price = db.Column(db.Float)
    low_price = db.Column(db.Float)
    volume = db.Column(db.BigInteger)
    market_cap = db.Column(db.BigInteger)
    pe_ratio = db.Column(db.Float)
    dividend_yield = db.Column(db.Float)
    change_percent = db.Column(db.Float)
    last_updated = db.Column(db.DateTime, default = datetime.utcnow)

    price_history = db.relationship("PriceHistory", backref = 'stock', lazy = True)

    def __repr__(self):
        return f"<StockDetails {self.ticker}>"

    
    
    
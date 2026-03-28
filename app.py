from flask import Flask
from config import Config
from models import db
from flask_login import LoginManager

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

from models import User

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Add this temporary route so Flask has something to work with
@app.route("/")
def index():
    return "Stock Tracker is running"

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)
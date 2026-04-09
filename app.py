from flask import Flask, redirect, render_template, url_for, request, flash, jsonify, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config
from models import db, User, StockDetails, SavedListItem, SavedList, PriceHistory
from alpha_vantage_service import get_top_gainers_losers, get_quote, get_daily_history
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from datetime import timedelta

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ── ROOT ──────────────────────────────────────────────────────
@app.route("/")
def index():
    return redirect(url_for("login"))


# ── REGISTER ──────────────────────────────────────────────────
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        email    = request.form.get("email")
        password = request.form.get("password")
        confirm  = request.form.get("confirm_password")

        if password != confirm:
            flash("Passwords do not match", "error")
            return redirect(url_for("register"))

        if User.query.filter_by(email=email).first():
            flash("Email already registered", "error")
            return redirect(url_for("register"))

        if User.query.filter_by(username=username).first():
            flash("Username already taken", "error")
            return redirect(url_for("register"))

        hashed = generate_password_hash(password)
        db.session.add(User(username=username, email=email, password=hashed))
        db.session.commit()

        flash("Account created successfully. Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


# ── LOGIN ─────────────────────────────────────────────────────
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email    = request.form.get("email")
        password = request.form.get("password")

        user = User.query.filter_by(email=email).first()
        print(user.password)
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash("Logged in successfully", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid email or password", "error")
            return redirect(url_for("login"))

    return render_template("login.html")


# ── LOGOUT ────────────────────────────────────────────────────
@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out successfully", "success")
    return redirect(url_for("login"))


# ── DASHBOARD ─────────────────────────────────────────────────
@app.route("/dashboard")
@login_required
def dashboard():
    # User's watched stocks
    user_lists = SavedList.query.filter_by(user_id=current_user.id).all()
    list_ids = [sl.id for sl in user_lists]
    saved_items = SavedListItem.query.filter(SavedListItem.saved_list_id.in_(list_ids)).all() if list_ids else []
    saved_tickers = list(set([item.ticker for item in saved_items]))
    
    watch_stocks = StockDetails.query.filter(StockDetails.ticker.in_(saved_tickers)).all() if saved_tickers else []
    
    # Recently viewed
    recent_tickers = session.get('recent_stocks', [])
    recent_stocks = []
    for t in recent_tickers:
        s = StockDetails.query.filter_by(ticker=t).first()
        if s: 
            recent_stocks.append(s)

    return render_template("dashboard.html", stocks=watch_stocks, recent_stocks=recent_stocks)

#---- All NAVBAR ROUTES ---------------------------------------
@app.route('/stocks')
@login_required
def stock_list():
    gainers, losers, most_active, last_updated = get_top_gainers_losers()

    user_lists    = SavedList.query.filter_by(user_id=current_user.id).all()
    list_ids      = [sl.id for sl in user_lists]
    saved_tickers = [item.ticker for item in
                     SavedListItem.query.filter(
                         SavedListItem.saved_list_id.in_(list_ids)
                     ).all()] if list_ids else []

    last_updated_str = last_updated.strftime("%d %b %Y, %H:%M") if last_updated else "—"

    return render_template('stock_list.html',
        gainers       = gainers,
        losers        = losers,
        most_active   = most_active,
        saved_tickers = saved_tickers,
        last_updated  = last_updated_str
    )

@app.route("/predict", methods=["GET"])
@login_required
def predict():
    ticker = request.args.get("ticker", "").strip().upper()
    
    # 1. Fetch user context for dropdown
    user_lists = SavedList.query.filter_by(user_id=current_user.id).all()
    list_ids = [sl.id for sl in user_lists]
    saved_items = SavedListItem.query.filter(SavedListItem.saved_list_id.in_(list_ids)).all() if list_ids else []
    saved_tickers = list(set([item.ticker for item in saved_items]))
    recent_tickers = session.get('recent_stocks', [])
    all_tickers = sorted(list(set(saved_tickers + recent_tickers)))
    
    if not ticker:
        return render_template("predict.html", all_tickers=all_tickers)
        
    # 2. Grab ticker data to predict
    stock = get_quote(ticker)
    history = get_daily_history(ticker)
    
    if not history or len(history) < 10:
        flash(f"Not enough historical data to generate an accurate forecast for {ticker}.", "error")
        return render_template("predict.html", all_tickers=all_tickers, ticker=ticker)

    # 3. Model Pipeline! (Pandas)
    data = [{"date": h.date, "close": h.close_price} for h in history]
    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    
    # Calculate Simple Moving Averages for Visuals
    df['SMA_10'] = df['close'].rolling(window=10).mean().fillna(df['close'])
    df['SMA_30'] = df['close'].rolling(window=30).mean().fillna(df['close'])
    
    # Calculate baseline days for model
    min_date = df['date'].min()
    df['days_since'] = (df['date'] - min_date).dt.days
    
    # 4. Scikit-Learn Model
    X = df[['days_since']].values
    y = df['close'].values
    
    model = LinearRegression()
    model.fit(X, y)
    
    # 5. Predict the next 5 business days
    last_date = df['date'].max()
    future_dates = []
    days_to_add = 1
    while len(future_dates) < 5:
        next_day = last_date + timedelta(days=days_to_add)
        if next_day.weekday() < 5: # Monday = 0, Friday = 4
            future_dates.append(next_day)
        days_to_add += 1
        
    future_days_since = [(d - min_date).days for d in future_dates]
    X_future = np.array(future_days_since).reshape(-1, 1)
    y_pred = model.predict(X_future)
    
    # 6. Format for Frontend Chart.js
    chart_dates = df['date'].dt.strftime('%Y-%m-%d').tolist()
    chart_prices = df['close'].tolist()
    chart_sma10 = df['SMA_10'].round(2).tolist()
    chart_sma30 = df['SMA_30'].round(2).tolist()
    
    future_chart_dates = [d.strftime('%Y-%m-%d') for d in future_dates]
    future_chart_prices = [round(float(p), 2) for p in y_pred]
    
    return render_template("predict.html",
        all_tickers=all_tickers,
        ticker=ticker,
        stock=stock,
        chart_dates=chart_dates,
        chart_prices=chart_prices,
        chart_sma10=chart_sma10,
        chart_sma30=chart_sma30,
        future_chart_dates=future_chart_dates,
        future_chart_prices=future_chart_prices
    )

@app.route("/stock/<ticker>")
@login_required
def stock_detail(ticker):
    ticker = ticker.upper()
    
    # Track recently viewed
    recent = session.get('recent_stocks', [])
    if ticker in recent:
        recent.remove(ticker)
    recent.insert(0, ticker)
    session['recent_stocks'] = recent[:5]
    session.modified = True
    
    stock = get_quote(ticker)
    history = get_daily_history(ticker)
    
    # IMPORT get_news_sentiment from alpha_vantage_service at the top, or just call it if already imported
    # Wait, need to ensure get_news_sentiment is imported
    from alpha_vantage_service import get_news_sentiment
    news_feed = get_news_sentiment(ticker)
    
    chart_dates = []
    chart_prices = []
    if history:
        for h in history:
            chart_dates.append(h.date.strftime("%Y-%m-%d"))
            chart_prices.append(h.close_price)
            
    return render_template(
        "stock_detail.html", 
        ticker=ticker,
        stock=stock,
        chart_dates=chart_dates,
        chart_prices=chart_prices,
        news=news_feed
    )

@app.route("/saved/add/<ticker>", methods=["POST"])
@login_required
def add_saved_stock(ticker):
    # 1. Get or create a default list for the user
    watchlist = SavedList.query.filter_by(user_id=current_user.id, name="My watchlist").first()
    if not watchlist:
        watchlist = SavedList(user_id=current_user.id, name="My watchlist")
        db.session.add(watchlist)
        db.session.commit()

    # 2. Check if already exists in this list
    existing = SavedListItem.query.filter_by(saved_list_id=watchlist.id, ticker=ticker).first()
    if not existing:
        new_item = SavedListItem(saved_list_id=watchlist.id, ticker=ticker)
        db.session.add(new_item)
        db.session.commit()
    
    return {"success": True}

@app.route("/saved/remove/<ticker>", methods=["POST"])
@login_required
def remove_saved_stock(ticker):
    # Get all user list IDs
    user_lists = SavedList.query.filter_by(user_id=current_user.id).all()
    list_ids = [sl.id for sl in user_lists]
    
    if list_ids:
        # Delete the ticker from any of the user's lists
        SavedListItem.query.filter(
            SavedListItem.saved_list_id.in_(list_ids),
            SavedListItem.ticker == ticker
        ).delete(synchronize_session=False)
        db.session.commit()
        
    return {"success": True}

@app.route("/saved")
@login_required
def saved_stocks():
    watchlists = SavedList.query.filter_by(user_id=current_user.id).all()

    # For each watchlist fetch the actual stock objects
    watchlist_data = []
    for wl in watchlists:
        tickers = [item.ticker for item in wl.items]
        stocks  = StockDetails.query.filter(
            StockDetails.ticker.in_(tickers)
        ).all() if tickers else []
        watchlist_data.append({
            "id":     wl.id,
            "name":   wl.name,
            "stocks": stocks
        })

    return render_template("saved.html", watchlist_data=watchlist_data)

# ── CREATE WATCHLIST ──────────────────────────────────────────
@app.route("/watchlist/create", methods=["POST"])
@login_required
def create_watchlist():
    name = request.form.get("name", "").strip()
    if not name:
        return jsonify({"success": False, "error": "Name required"})

    exists = SavedList.query.filter_by(
        user_id=current_user.id, name=name
    ).first()

    if exists:
        return jsonify({"success": False, "error": "Watchlist already exists"})

    new_list = SavedList(user_id=current_user.id, name=name)
    db.session.add(new_list)
    db.session.commit()

    return jsonify({"success": True, "id": new_list.id, "name": new_list.name})


# ── DELETE WATCHLIST ──────────────────────────────────────────
@app.route("/watchlist/delete/<int:list_id>", methods=["POST"])
@login_required
def delete_watchlist(list_id):
    watchlist = SavedList.query.filter_by(
        id=list_id, user_id=current_user.id
    ).first()

    if watchlist:
        SavedListItem.query.filter_by(saved_list_id=list_id).delete()
        db.session.delete(watchlist)
        db.session.commit()

    return jsonify({"success": True})


# ── ADD STOCK TO SPECIFIC WATCHLIST ───────────────────────────
@app.route("/watchlist/<int:list_id>/add/<ticker>", methods=["POST"])
@login_required
def add_to_watchlist(list_id, ticker):
    watchlist = SavedList.query.filter_by(
        id=list_id, user_id=current_user.id
    ).first()

    if not watchlist:
        return jsonify({"success": False, "error": "Watchlist not found"})

    exists = SavedListItem.query.filter_by(
        saved_list_id=list_id, ticker=ticker.upper()
    ).first()

    if not exists:
        db.session.add(SavedListItem(
            saved_list_id=list_id,
            ticker=ticker.upper()
        ))
        db.session.commit()

    return jsonify({"success": True})


# ── REMOVE STOCK FROM WATCHLIST ───────────────────────────────
@app.route("/watchlist/<int:list_id>/remove/<ticker>", methods=["POST"])
@login_required
def remove_from_watchlist(list_id, ticker):
    item = SavedListItem.query.filter_by(
        saved_list_id=list_id,
        ticker=ticker.upper()
    ).first()

    if item:
        db.session.delete(item)
        db.session.commit()

    return jsonify({"success": True})


# ── GET USER WATCHLISTS (for modal) ───────────────────────────
@app.route("/watchlists", methods=["GET"])
@login_required
def get_watchlists():
    lists = SavedList.query.filter_by(user_id=current_user.id).all()
    return jsonify([{"id": l.id, "name": l.name} for l in lists])

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)
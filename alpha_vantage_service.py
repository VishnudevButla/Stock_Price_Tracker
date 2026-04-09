import os
import requests
from datetime import datetime, timedelta
from models import db, StockDetails, PriceHistory

API_KEY = os.getenv("ALPHA_VANTAGE_KEY")
BASE_URL = "https://www.alphavantage.co/query"


# ─── HELPER ───────────────────────────────────────────────────────────────────
# This is the main function that gets the data from the API.
# It is called helper because instead of typing params["apikey"] = API_KEY
# every time we want to get data from the API, we can just call this function.
# The _ indicates it is a helper function and is supposed to be used only in this file.
def _get(params):
    params["apikey"] = API_KEY
    try:
        r = requests.get(BASE_URL, params=params, timeout=10)
        return r.json()
    except Exception:
        return {}


# ─── TOP GAINERS / LOSERS / MOST ACTIVE ───────────────────────────────────────
# This is the key function for your stock list page.
# It costs only 1 API call and returns all three lists at once.
# We cache the results in the database for 24 hours so we don't
# waste API calls fetching the same data repeatedly.

def get_top_gainers_losers():
    # Check if we already fetched today
    sample = StockDetails.query.filter(
        StockDetails.last_updated >= datetime.utcnow() - timedelta(hours=24)
    ).first()

    if sample:
        # Return cached data from database — no API call needed
        gainers     = StockDetails.query.filter(StockDetails.change_percent > 0)\
                                        .order_by(StockDetails.change_percent.desc())\
                                        .limit(20).all()
        losers      = StockDetails.query.filter(StockDetails.change_percent < 0)\
                                        .order_by(StockDetails.change_percent.asc())\
                                        .limit(20).all()
        most_active = StockDetails.query.order_by(StockDetails.volume.desc())\
                                        .limit(20).all()
        return gainers, losers, most_active, sample.last_updated

    # Cache is stale — fetch fresh data from Alpha Vantage
    data = _get({"function": "TOP_GAINERS_LOSERS"})

    if "top_gainers" not in data:
        # API call failed — return whatever is in DB even if stale
        print("API call failed — returning cached data")
        gainers     = StockDetails.query.filter(StockDetails.change_percent > 0)\
                                        .order_by(StockDetails.change_percent.desc()).limit(20).all()
        losers      = StockDetails.query.filter(StockDetails.change_percent < 0)\
                                        .order_by(StockDetails.change_percent.asc()).limit(20).all()
        most_active = StockDetails.query.order_by(StockDetails.volume.desc()).limit(20).all()
        return gainers, losers, most_active, None

    # Save each stock into the database
    def save_list(raw_list):
        saved = []
        for item in raw_list:
            ticker = item.get("ticker", "")
            if not ticker:
                continue

            stock = StockDetails.query.filter_by(ticker=ticker).first()
            if not stock:
                stock = StockDetails(ticker=ticker)
                db.session.add(stock)

            stock.company_name   = item.get("ticker", ticker)
            stock.current_price  = _safe_float(item.get("price"))
            stock.change_percent = _safe_float(item.get("change_percentage", "").replace("%", ""))
            stock.volume         = _safe_int(item.get("volume"))
            stock.last_updated   = datetime.utcnow()
            saved.append(stock)

        db.session.commit()
        return saved

    gainers     = save_list(data.get("top_gainers",     []))
    losers      = save_list(data.get("top_losers",      []))
    most_active = save_list(data.get("most_actively_traded", []))
    last_updated = datetime.utcnow()

    return gainers, losers, most_active, last_updated


# ─── LIVE QUOTE (single stock) ────────────────────────────────────────────────
# Used on the stock detail page.
# Costs 1 API call per stock.
# Caches in DB — only re-fetches if data is older than 15 minutes.

def get_quote(ticker):
    stock = StockDetails.query.filter_by(ticker=ticker).first()

    # Return cached if fresh enough
    if stock and stock.last_updated:
        age = datetime.utcnow() - stock.last_updated
        if age < timedelta(minutes=15):
            return stock

    # Fetch fresh quote
    data = _get({"function": "GLOBAL_QUOTE", "symbol": ticker})
    quote = data.get("Global Quote", {})

    if not quote:
        return stock  # return stale data rather than nothing

    if not stock:
        stock = StockDetails(ticker=ticker)
        db.session.add(stock)

    stock.current_price  = _safe_float(quote.get("05. price"))
    stock.open_price     = _safe_float(quote.get("02. open"))
    stock.high_price     = _safe_float(quote.get("03. high"))
    stock.low_price      = _safe_float(quote.get("04. low"))
    stock.volume         = _safe_int(quote.get("06. volume"))
    stock.change_percent = _safe_float(quote.get("10. change percent", "").replace("%", ""))
    stock.last_updated   = datetime.utcnow()

    db.session.commit()
    return stock


# ─── HISTORICAL PRICES (for chart) ────────────────────────────────────────────
# Used on the stock detail page to draw the Chart.js graph.
# Fetches daily OHLCV data for up to 20 years.
# Costs 1 API call — only re-fetches if no data exists for this stock.

def get_daily_history(ticker):
    stock = StockDetails.query.filter_by(ticker=ticker).first()
    if not stock:
        return []

    # If we already have recent history, return it from DB
    latest = PriceHistory.query.filter_by(stock_id=stock.id)\
                                .order_by(PriceHistory.date.desc()).first()

    today = datetime.utcnow().date()
    if latest and (today - latest.date).days <= 1:
        return PriceHistory.query.filter_by(stock_id=stock.id)\
                                 .order_by(PriceHistory.date.asc()).all()

    data = _get({
        "function":   "TIME_SERIES_DAILY",
        "symbol":     ticker,
        "outputsize": "compact"  # last 100 data points
    })

    time_series = data.get("Time Series (Daily)", {})
    if not time_series:
        return []

    # Fetch all existing dates for this stock upfront to avoid autoflush IntegrityErrors
    existing_records = PriceHistory.query.filter_by(stock_id=stock.id).all()
    existing_dates = {rec.date for rec in existing_records}

    # Save each day to database
    for date_str, values in time_series.items():
        try:
            date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            continue

        if date not in existing_dates:
            db.session.add(PriceHistory(
                stock_id    = stock.id,
                date        = date,
                open_price  = _safe_float(values.get("1. open")),
                high_price  = _safe_float(values.get("2. high")),
                low_price   = _safe_float(values.get("3. low")),
                close_price = _safe_float(values.get("4. close")),
                volume      = _safe_int(values.get("5. volume")),
            ))
            existing_dates.add(date)

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error saving price history: {e}")

    return PriceHistory.query.filter_by(stock_id=stock.id)\
                             .order_by(PriceHistory.date.asc()).all()


# ─── INTRADAY PRICES (for 5min / 2hr ranges on chart) ─────────────────────────
# Costs 1 API call.
# Returns intraday prices at a given interval.

def get_intraday(ticker, interval="5min"):
    data = _get({
        "function": "TIME_SERIES_INTRADAY",
        "symbol":   ticker,
        "interval": interval,
        "outputsize": "compact"  # last 100 data points
    })

    key = f"Time Series ({interval})"
    time_series = data.get(key, {})

    result = []
    for dt_str, values in sorted(time_series.items()):
        result.append({
            "datetime": dt_str,
            "open":     _safe_float(values.get("1. open")),
            "high":     _safe_float(values.get("2. high")),
            "low":      _safe_float(values.get("3. low")),
            "close":    _safe_float(values.get("4. close")),
            "volume":   _safe_int(values.get("5. volume")),
        })

    return result


# ─── SAFE TYPE CONVERTERS ─────────────────────────────────────────────────────
def _safe_float(val):
    try:
        return float(val)
    except (TypeError, ValueError):
        return None

def _safe_int(val):
    try:
        return int(float(str(val).replace(",", "")))
    except (TypeError, ValueError):
        return None

# ─── NEWS SENTIMENT ───────────────────────────────────────────────────────────
# Costs 1 API call per stock.
# Returns recent news articles and their AI sentiment classification.

def get_news_sentiment(ticker):
    data = _get({
        "function": "NEWS_SENTIMENT",
        "tickers": ticker,
        "limit": 5
    })
    return data.get("feed", [])
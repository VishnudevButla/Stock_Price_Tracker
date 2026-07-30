# QuantIQ — Stock Price Tracker & Predictor

> A full-stack web application for tracking real-time stock prices, analysing market movers, managing personal watchlists, and generating 5-day price forecasts using machine learning.

🌐 **Live Demo:** [https://quantiq-egq1.onrender.com](https://quantiq-egq1.onrender.com)

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Environment Variables](#environment-variables)
  - [Running Locally](#running-locally)
- [Architecture & Data Flow](#architecture--data-flow)
- [API Usage & Caching Strategy](#api-usage--caching-strategy)
- [Database Models](#database-models)
- [Deployment](#deployment)
- [License](#license)

---

## Overview

QuantIQ is a Python/Flask web application that lets registered users monitor the US stock market in one place. It pulls live data from the **Alpha Vantage API**, caches it intelligently in a **PostgreSQL** database (Neon), and exposes a clean, templated UI. A lightweight **scikit-learn Linear Regression** model produces short-term (5-business-day) price forecasts for any ticker in the user's watchlist.

---

## Features

| Feature | Description |
|---|---|
| 🔐 **User Auth** | Secure registration & login with hashed passwords (Werkzeug) |
| 📈 **Market Movers** | Top 20 gainers, losers, and most-active stocks via Alpha Vantage |
| 🔍 **Stock Detail Page** | Live quote (price, open, high, low, volume, % change) + interactive Chart.js historical chart |
| 📰 **News Sentiment** | Latest 5 news articles with AI sentiment classification per ticker |
| 🗂️ **Watchlists** | Create, rename, and delete multiple named watchlists; add/remove any ticker |
| 🕐 **Recently Viewed** | Session-based history of the last 5 stocks viewed |
| 🤖 **Price Prediction** | 5-business-day forecast using Linear Regression + SMA-10 & SMA-30 overlays |
| 💾 **Smart Caching** | DB-level caching prevents redundant API calls (quotes: 15 min, movers: 24 hr) |
| ☁️ **Cloud Deployment** | Deployed on Render with Gunicorn; PostgreSQL hosted on Neon |

---

## Tech Stack

### Backend
- **Python 3.11**
- **Flask 3.1** — web framework
- **Flask-Login** — session-based authentication
- **Flask-SQLAlchemy 3.1** — ORM
- **Werkzeug** — password hashing
- **Gunicorn** — WSGI production server

### Database
- **PostgreSQL** (Neon serverless, production)
- **SQLite** (local development fallback via `sqlite:///dev.db`)

### Data & ML
- **Alpha Vantage API** — live stock quotes, daily history, market movers, news sentiment
- **pandas** — time-series data manipulation
- **NumPy** — numerical arrays for model input
- **scikit-learn** — `LinearRegression` for price forecasting

### Frontend
- **Jinja2** templates
- **Chart.js** — interactive price & prediction charts

---

## Project Structure

```
Stock_price_Tracker/
├── app.py                    # Flask app factory, all route definitions
├── alpha_vantage_service.py  # Alpha Vantage API client + DB caching layer
├── models.py                 # SQLAlchemy ORM models
├── config.py                 # App configuration (env vars, DB URL, engine options)
├── templates/
│   ├── base.html             # Shared layout & navbar
│   ├── login.html            # Login page
│   ├── register.html         # Registration page
│   ├── dashboard.html        # User dashboard (watchlist + recent stocks)
│   ├── stock_list.html       # Gainers / losers / most-active tables
│   ├── stock_detail.html     # Single stock detail + chart + news
│   ├── predict.html          # ML price prediction page
│   └── saved.html            # All watchlists management
├── requirements.txt          # Python dependencies
├── Procfile                  # Heroku/Render process declaration
├── render.yaml               # Render deployment config
├── runtime.txt               # Python version pin (3.11.0)
└── .env                      # Local environment variables (not committed)
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- A free [Alpha Vantage API key](https://www.alphavantage.co/support/#api-key)
- PostgreSQL instance **or** use the SQLite fallback for local dev

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/VishnudevButla/QuantIQ.git
cd QuantIQ

# 2. Create and activate a virtual environment
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file in the project root:

```env
# Alpha Vantage API key
ALPHA_VANTAGE_KEY=your_api_key_here

# PostgreSQL connection string (or leave blank for SQLite fallback)
DATABASE_URL=postgresql://user:password@host/dbname

# Flask secret key (generate a secure random string)
SECRET_KEY=your_secret_key_here
```

> **Note:** For local development without PostgreSQL, omit `DATABASE_URL` entirely. The app will automatically fall back to a local `dev.db` SQLite file.

### Running Locally

```bash
python app.py
```

The app will be available at `http://127.0.0.1:5000`.

The database tables are created automatically on first run via `db.create_all()`.

---

## Architecture & Data Flow

```
Browser (User)
     │
     ▼
Flask Routes (app.py)
     │
     ├── Authentication ──► User model (PostgreSQL/SQLite)
     │
     ├── /stocks ──────────► alpha_vantage_service.get_top_gainers_losers()
     │                            │
     │                            ├─ Cache hit?  ──► Return from DB (no API call)
     │                            └─ Cache miss? ──► Alpha Vantage API ──► Save to DB
     │
     ├── /stock/<ticker> ──► get_quote()  [15-min cache]
     │                  └──► get_daily_history() [1-day cache]
     │                  └──► get_news_sentiment() [live, no cache]
     │
     └── /predict ─────────► get_daily_history() ──► pandas DataFrame
                                  └──► scikit-learn LinearRegression
                                            └──► 5-day forecast ──► Chart.js
```

---

## API Usage & Caching Strategy

Alpha Vantage's free tier is rate-limited (25 calls/day on the free plan). QuantIQ minimises API consumption with a two-tier caching strategy:

| Endpoint | Cache Duration | Logic |
|---|---|---|
| `TOP_GAINERS_LOSERS` | **24 hours** | Stored in `StockDetails`; returns DB data if any record is fresher than 24 h |
| `GLOBAL_QUOTE` | **15 minutes** | Per-ticker `last_updated` timestamp check; serves stale data if API is unreachable |
| `TIME_SERIES_DAILY` | **1 day** | Checks most recent `PriceHistory` date; only fetches if today's data is missing |
| `NEWS_SENTIMENT` | **No cache** | Always fetched live (only called on stock detail page) |
| `TIME_SERIES_INTRADAY` | **No cache** | Available via `get_intraday()` helper |

---

## Database Models

### `User`
| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | Auto-increment |
| `username` | String(256) | Unique |
| `email` | String(120) | Unique |
| `password` | String(512) | Werkzeug hash |
| `created_at` | DateTime | Auto-set |

### `StockDetails`
| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | |
| `ticker` | String(10) | e.g. `AAPL` |
| `current_price` | Float | |
| `open/high/low_price` | Float | |
| `volume` | BigInteger | |
| `change_percent` | Float | |
| `last_updated` | DateTime | Used for cache invalidation |

### `PriceHistory`
| Column | Type | Notes |
|---|---|---|
| `stock_id` | FK → `stocks.id` | |
| `date` | Date | |
| `open/high/low/close_price` | Float | OHLC daily data |
| `volume` | BigInteger | |

Unique constraint on `(stock_id, date)` prevents duplicates.

### `SavedList` & `SavedListItem`
Many-to-many between `User` and ticker symbols, namespaced per watchlist.
- A user can have multiple named watchlists.
- Each `SavedListItem` holds a `ticker` string under a `SavedList`.
- Unique constraint on `(saved_list_id, ticker)` prevents duplicate entries.

---

## Deployment

The app is deployed on **[Render](https://render.com)** using Gunicorn.

### Render Configuration (`render.yaml`)
```yaml
services:
  - type: web
    name: stock-tracker
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn app:app
    envVars:
      - key: ALPHA_VANTAGE_KEY
      - key: SECRET_KEY
      - key: DATABASE_URL
```

Set the three environment variables (`ALPHA_VANTAGE_KEY`, `SECRET_KEY`, `DATABASE_URL`) in the Render dashboard under **Environment**. The PostgreSQL database is hosted on **[Neon](https://neon.tech)** (serverless Postgres). The `pool_pre_ping` and `pool_recycle` engine options in `config.py` keep the connection alive after Neon's auto-suspend periods.

---

## License

This project is open-source. See the repository at [github.com/VishnudevButla/QuantIQ](https://github.com/VishnudevButla/QuantIQ/) for the full source code.

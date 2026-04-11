# QuantIQ
Intelligent Stock Market Analyser

A real-time stock price tracking and analytics web application built with Python, Flask, and PostgreSQL. Users can monitor live market data, track top gainers and losers, manage custom watchlists, and view interactive price charts with moving averages.

**Live Demo:** https://quantiq-egq1.onrender.com.

---

## Features

- **Live market data** — real-time stock quotes powered by the Alpha Vantage REST API
- **Top gainers / losers / most active** — market overview refreshed every 24 hours with intelligent caching
- **Interactive charts** — historical price charts with 5min, 2hr, daily, weekly, and yearly ranges built with Chart.js
- **Moving averages** — 7-day and 30-day moving averages calculated and overlaid on price charts
- **Custom watchlists** — create, name, and manage multiple personal stock watchlists
- **Stock detail page** — full OHLCV data, percentage change, volume, and market depth per stock
- **Price prediction** — ML-based price forecasting for individual stocks
- **Secure authentication** — user registration and login with bcrypt password hashing via Flask-Login
- **Responsive UI** — dark-themed, terminal-style interface optimised for both desktop and mobile

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11, Flask |
| Database | PostgreSQL (Neon serverless) |
| ORM | SQLAlchemy |
| Authentication | Flask-Login, Werkzeug |
| Market Data | Alpha Vantage REST API |
| Charts | Chart.js |
| Frontend | HTML5, CSS3, Vanilla JavaScript, Jinja2 |
| Deployment | Render |
| Version Control | Git, GitHub |

---

## Project Structure

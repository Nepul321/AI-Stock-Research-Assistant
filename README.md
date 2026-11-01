# AI Stock Research Assistant

> 🚧 **Work in Progress:** This project is currently under active development. Features, architecture, and technologies may change as development continues.

An AI-powered stock research assistant built with **Django**, **Django REST Framework**, **Finnhub API**, and **Bootstrap**.

The goal of this project is to create a platform where users can research stocks, manage personal watchlists, access company and market information, and use AI-powered tools to better understand financial data.

For the AI portion of the project, I may use either the **Anthropic Claude API** or **OpenAI API**. The final provider has not yet been decided.

## Features

- User registration and login
- Session authentication
- JWT authentication
- Account management and password changes
- Stock search and validation through Finnhub
- Company profiles and market data
- Personal stock watchlists
- REST API built with Django REST Framework
- AI-powered stock research and summaries
- AI-assisted explanations of financial information
- Bootstrap-based frontend
- Historical stock data and charts
- News analysis and summarization

## Tech Stack

- **Python**
- **Django**
- **Django REST Framework**
- **SQLite** for development
- **PostgreSQL** planned
- **Finnhub API**
- **finnhub-python**
- **Bootstrap**
- **Django Templates**
- **JWT Authentication**
- **Anthropic Claude API or OpenAI API** for planned AI functionality

## AI Assistance

- Used GitHub Copilot to assist with code generation, debugging, and development.

## Architecture

The project uses a service layer to separate external financial data integrations from the Django application logic.

Finnhub functionality is handled through a dedicated service, making the external API integration easier to maintain and extend as the project grows.

## REST API authentication

The API accepts either the existing Django session or a JWT access token for protected endpoints. Access follows the frontend: stock, watchlist, portfolio, and password-change endpoints require authentication; registration and token login are available only to anonymous users.

- `POST /api/users/register/` — register with `username`, `email`, `password`, and `confirm_password`.
- `POST /api/token/` — obtain an access/refresh token pair with `username` and `password`.
- `POST /api/token/refresh/` — rotate a refresh token by sending `refresh`; use the returned refresh token thereafter.
- `POST /api/token/logout/` — revoke a refresh token by sending `refresh` with the authenticated user's access token.
- `POST /api/users/change-password/` — authenticated; send `old_password`, `new_password`, and `confirm_password`.
- `POST /api/users/password-reset/` — request a reset email using `email`. The response does not disclose whether that account exists.
- `POST /api/users/password-reset/confirm/` — reset using `uidb64`, `token`, `new_password`, and `confirm_password`.

Access tokens expire after five minutes and refresh tokens after one day. Refresh tokens rotate and are blacklisted when replaced or logged out; password changes and resets invalidate outstanding tokens.
After changing a password through the API, clients should discard their stored access and refresh tokens; those credentials are already invalid, so the logout endpoint cannot authenticate them. A new token pair can be obtained by logging in with the new password.
Run `python manage.py migrate` when deploying the token blacklist app, and schedule Django's `flushexpiredtokens` management command to remove expired token records.

API errors use the same envelope for validation, authentication, permission, and expected application errors:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Request validation failed.",
    "details": {
      "email": ["Enter a valid email address."]
    }
  }
}
```

## Portfolio value history

Portfolio values are saved as daily snapshots. The capture function first tries Finnhub daily closing candles. If Finnhub returns HTTP 403 for candles (for example, when the account does not have access to that endpoint), it falls back to current quotes for every held stock, so a portfolio is priced consistently. Quote-based snapshots are dated on the capture day and reflect the quote at the time the job runs; schedule the job after market close for an end-of-day trend. Other price errors fail the run rather than saving a partial portfolio value. The portfolio detail page charts up to the latest 365 saved values. Existing portfolios have no historical snapshots to backfill; their charts build from the first scheduled capture onward.

Run a capture manually from the directory containing `manage.py`:

```powershell
python manage.py capture_portfolio_snapshots
```

Schedule this command once per weekday after the US market close using the production platform's scheduler (for example, cron, a container scheduled job, or a hosted scheduler). No task-queue dependency is required. The underlying `capture_daily_portfolio_snapshots()` function in `portfolios.services` is also independent of the command, so a Celery task can call it directly when Celery is added. When candle access is available, a portfolio's point uses its latest common trading date; in quote fallback mode, all holdings use quotes captured on the scheduled run date.

## Disclaimer

**For Educational and Informational Purposes Only**

This project is currently under development and is intended for educational and portfolio purposes only.

The information, market data, AI-generated content, summaries, and analysis provided by this application are **not intended to constitute financial, investment, legal, or professional advice**.

AI-generated responses may contain inaccuracies, outdated information, or misinterpretations. Users should independently verify information and consult a qualified financial professional before making any investment decisions.

This application does not guarantee the accuracy, completeness, or timeliness of any financial information and should not be relied upon as a basis for making investment decisions.

**Do not use this application as a substitute for professional financial advice.**

## License

License information will be added as the project develops.
# AI Stock Research Assistant

> 🚧 **Work in Progress:** This project is currently under active development. Features, architecture, and technologies may change as development continues.

An AI-powered stock research assistant built with **Django**, **Django REST Framework**, **Finnhub API**, and **Bootstrap**.

The goal of this project is to create a platform where users can research stocks, manage personal watchlists, access company and market information, and use AI-powered tools to better understand financial data.

For the AI portion of the project, I may use either the **Anthropic Claude API** or **Google Gemini API**. The final provider has not yet been decided.

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
- **Anthropic Claude API or Google Gemini API** for planned AI functionality

## Architecture

The project uses a service layer to separate external financial data integrations from the Django application logic.

Finnhub functionality is handled through a dedicated service, making the external API integration easier to maintain and extend as the project grows.

## Disclaimer

**For Educational and Informational Purposes Only**

This project is currently under development and is intended for educational and portfolio purposes only.

The information, market data, AI-generated content, summaries, and analysis provided by this application are **not intended to constitute financial, investment, legal, or professional advice**.

AI-generated responses may contain inaccuracies, outdated information, or misinterpretations. Users should independently verify information and consult a qualified financial professional before making any investment decisions.

This application does not guarantee the accuracy, completeness, or timeliness of any financial information and should not be relied upon as a basis for making investment decisions.

**Do not use this application as a substitute for professional financial advice.**

## License

License information will be added as the project develops.
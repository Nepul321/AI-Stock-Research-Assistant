import json

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from openai import OpenAI

from portfolios.models import Portfolio
from stocks.models import Stock


class OpenAIService:
    instructions = (
        "You provide clear, balanced investing information for educational "
        "purposes. Explain uncertainty and relevant risks, do not promise "
        "returns, and do not invent current market data. The response is not "
        "a substitute for advice from a qualified financial professional."
    )

    def __init__(self, client: OpenAI | None = None):
        api_key = settings.OPENAI_API_KEY
        model = settings.OPENAI_MODEL
        if not api_key:
            raise ImproperlyConfigured("OPENAI_API_KEY is not configured.")
        if not model:
            raise ImproperlyConfigured("OPENAI_MODEL is not configured.")

        self.client = client if client is not None else OpenAI(api_key=api_key)
        self.model = model

    def get_general_advice(self, question: str) -> str:
        return self._get_advice(
            question,
            "No portfolio or stock-specific information was provided.",
        )

    def get_portfolio_advice(self, question: str, portfolio: Portfolio) -> str:
        holdings = [
            {
                "symbol": holding.stock.symbol,
                "company_name": holding.stock.company_name,
                "shares": str(holding.amount),
            }
            for holding in portfolio.portfolio_stocks.select_related("stock")
        ]
        context = {
            "portfolio_name": portfolio.name,
            "holdings": holdings,
            "latest_snapshot": None,
        }

        snapshot = portfolio.value_snapshots.order_by("-date").first()
        if snapshot is not None:
            context["latest_snapshot"] = {
                "date": snapshot.date.isoformat(),
                "value": str(snapshot.value),
                "currency": snapshot.currency,
            }

        return self._get_advice(question, json.dumps(context))

    def get_stock_advice(self, question: str, stock: Stock) -> str:
        context = {
            "symbol": stock.symbol,
            "company_name": stock.company_name,
            "exchange": stock.exchange,
            "market_data": "No live market data was provided.",
        }
        return self._get_advice(question, json.dumps(context))

    def _get_advice(self, question: str, context: str) -> str:
        question = question.strip()
        if not question:
            raise ValueError("A question is required.")

        response = self.client.responses.create(
            model=self.model,
            instructions=self.instructions,
            input=f"Context:\n{context}\n\nQuestion:\n{question}",
        )
        advice = response.output_text.strip()
        if not advice:
            raise RuntimeError("The OpenAI API returned an empty advice response.")
        return advice

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, override_settings

from advice.api.main import OpenAIService


@override_settings(OPENAI_API_KEY="test-key", OPENAI_MODEL="test-model")
class OpenAIServiceTests(SimpleTestCase):
    def setUp(self):
        self.client = Mock()
        self.client.responses.create.return_value = SimpleNamespace(
            output_text="Consider the risks and your time horizon."
        )
        self.service = OpenAIService(client=self.client)

    def test_get_general_advice_sends_question_and_returns_response(self):
        advice = self.service.get_general_advice("How should I diversify?")

        self.assertEqual(advice, "Consider the risks and your time horizon.")
        self.client.responses.create.assert_called_once()
        request = self.client.responses.create.call_args.kwargs
        self.assertEqual(request["model"], "test-model")
        self.assertIn("How should I diversify?", request["input"])

    def test_get_portfolio_advice_includes_holdings_and_latest_snapshot(self):
        snapshot = SimpleNamespace(
            date=SimpleNamespace(isoformat=lambda: "2026-11-10"),
            value=Decimal("1250.5000"),
            currency="USD",
        )
        portfolio = SimpleNamespace(
            name="Retirement",
            portfolio_stocks=SimpleNamespace(
                select_related=Mock(
                    return_value=[
                        SimpleNamespace(
                            stock=SimpleNamespace(
                                symbol="ACME",
                                company_name="Acme Inc.",
                            ),
                            amount=Decimal("2.5000"),
                        )
                    ]
                )
            ),
            value_snapshots=SimpleNamespace(
                order_by=Mock(return_value=SimpleNamespace(first=lambda: snapshot))
            ),
        )

        self.service.get_portfolio_advice("Review my allocation", portfolio)

        request = self.client.responses.create.call_args.kwargs
        self.assertIn('"symbol": "ACME"', request["input"])
        self.assertIn('"shares": "2.5000"', request["input"])
        self.assertIn('"value": "1250.5000"', request["input"])

    def test_get_stock_advice_includes_stock_details_and_no_live_data_notice(self):
        stock = SimpleNamespace(
            symbol="ACME",
            company_name="Acme Inc.",
            exchange="NYSE",
        )

        self.service.get_stock_advice("What are the risks?", stock)

        request = self.client.responses.create.call_args.kwargs
        self.assertIn('"symbol": "ACME"', request["input"])
        self.assertIn('"exchange": "NYSE"', request["input"])
        self.assertIn("No live market data was provided.", request["input"])

    def test_missing_api_key_is_reported(self):
        with override_settings(OPENAI_API_KEY=""):
            with self.assertRaisesMessage(
                ImproperlyConfigured,
                "OPENAI_API_KEY is not configured.",
            ):
                OpenAIService()

    def test_empty_question_is_rejected(self):
        with self.assertRaisesMessage(ValueError, "A question is required."):
            self.service.get_general_advice("  ")

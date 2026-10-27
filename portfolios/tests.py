from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction
from django.urls import reverse
from unittest.mock import patch
from rest_framework.test import APITestCase

from portfolios.models import Portfolio, PortfolioStock
from stocks.models import Stock
from watchlists.models import Watchlist


class PortfolioStockTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='portfolio-user')
        cls.other_user = User.objects.create_user(username='other-user')
        cls.stock = Stock(symbol='AAPL', company_name='Apple', exchange='NASDAQ')
        cls.other_stock = Stock(symbol='MSFT', company_name='Microsoft', exchange='NASDAQ')
        Stock.objects.bulk_create([cls.stock, cls.other_stock])
        cls.portfolio = Portfolio.objects.create(user=cls.user, name='My portfolio')

    def test_portfolio_accepts_stock_in_any_user_watchlist(self):
        Watchlist.objects.create(user=self.user, name='Tech')
        second_watchlist = Watchlist.objects.create(user=self.user, name='Favorites')
        second_watchlist.stocks.add(self.stock)

        self.portfolio.stocks.add(self.stock)

        self.assertIn(self.stock, self.portfolio.stocks.all())

    def test_portfolio_rejects_stock_not_in_user_watchlist(self):
        other_watchlist = Watchlist.objects.create(user=self.other_user, name='Other')
        other_watchlist.stocks.add(self.other_stock)

        with transaction.atomic():
            with self.assertRaises(ValidationError):
                self.portfolio.stocks.add(self.other_stock)

        self.assertFalse(self.portfolio.stocks.filter(pk=self.other_stock.pk).exists())

    def test_through_model_rejects_stock_not_in_user_watchlist(self):
        with self.assertRaises(ValidationError):
            PortfolioStock.objects.create(
                portfolio=self.portfolio,
                stock=self.other_stock,
            )

    def test_removing_last_watchlist_membership_removes_portfolio_stock(self):
        watchlist = Watchlist.objects.create(user=self.user, name='Tech')
        watchlist.stocks.add(self.stock)
        self.portfolio.stocks.add(self.stock)

        watchlist.stocks.remove(self.stock)

        self.assertFalse(self.portfolio.stocks.filter(pk=self.stock.pk).exists())

    def test_removing_watchlist_membership_keeps_stock_if_another_watchlist_has_it(self):
        first_watchlist = Watchlist.objects.create(user=self.user, name='Tech')
        second_watchlist = Watchlist.objects.create(user=self.user, name='Favorites')
        first_watchlist.stocks.add(self.stock)
        second_watchlist.stocks.add(self.stock)
        self.portfolio.stocks.add(self.stock)

        first_watchlist.stocks.remove(self.stock)

        self.assertTrue(self.portfolio.stocks.filter(pk=self.stock.pk).exists())

    def test_deleting_last_watchlist_removes_portfolio_stock(self):
        watchlist = Watchlist.objects.create(user=self.user, name='Tech')
        watchlist.stocks.add(self.stock)
        self.portfolio.stocks.add(self.stock)

        watchlist.delete()

        self.assertFalse(self.portfolio.stocks.filter(pk=self.stock.pk).exists())


class PortfolioFrontendTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="portfolio-page-user")
        self.other_user = User.objects.create_user(username="other-page-user")
        self.portfolio = Portfolio.objects.create(
            user=self.user,
            name="Long-term",
        )
        self.client.force_login(self.user)

    def test_portfolio_list_includes_create_form(self):
        response = self.client.get(reverse("portfolios"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create a portfolio")
        self.assertContains(response, self.portfolio.name)

    def test_invalid_create_renders_form_errors(self):
        response = self.client.post(reverse("portfolio_create"), {"name": ""})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This field is required.")

    def test_create_portfolio_assigns_current_user(self):
        response = self.client.post(
            reverse("portfolio_create"),
            {"name": "Retirement"},
        )

        self.assertRedirects(response, reverse("portfolios"))
        portfolio = Portfolio.objects.get(name="Retirement")
        self.assertEqual(portfolio.user, self.user)

    def test_update_portfolio(self):
        response = self.client.post(
            reverse("portfolio_update", args=[self.portfolio.pk]),
            {"name": "Updated portfolio"},
        )

        self.assertRedirects(
            response,
            reverse("portfolio_detail_delete", args=[self.portfolio.pk]),
        )
        self.portfolio.refresh_from_db()
        self.assertEqual(self.portfolio.name, "Updated portfolio")

    @patch("portfolios.views.FinnhubService")
    def test_update_and_detail_pages_render(self, finnhub_service):
        stock = Stock(symbol="AAPL", company_name="Apple", exchange="NASDAQ")
        Stock.objects.bulk_create([stock])
        watchlist = Watchlist.objects.create(user=self.user, name="Tech")
        watchlist.stocks.add(stock)
        PortfolioStock.objects.create(
            portfolio=self.portfolio, stock=stock, amount="2.0000"
        )
        finnhub_service.return_value.get_stock_quote.return_value = {"c": 150.25}

        update_response = self.client.get(
            reverse("portfolio_update", args=[self.portfolio.pk])
        )
        detail_response = self.client.get(
            reverse("portfolio_detail_delete", args=[self.portfolio.pk])
        )

        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, "AAPL")
        self.assertContains(detail_response, "Total portfolio value")
        self.assertContains(detail_response, "$300.50")
        self.assertContains(detail_response, "portfolio_value.js")

    @patch("portfolios.views.FinnhubService")
    def test_portfolio_value_returns_sum_of_holdings(self, finnhub_service):
        first_stock = Stock(symbol="AAPL", company_name="Apple", exchange="NASDAQ")
        second_stock = Stock(symbol="MSFT", company_name="Microsoft", exchange="NASDAQ")
        Stock.objects.bulk_create([first_stock, second_stock])
        watchlist = Watchlist.objects.create(user=self.user, name="Tech")
        watchlist.stocks.add(first_stock, second_stock)
        PortfolioStock.objects.create(
            portfolio=self.portfolio, stock=first_stock, amount="10.0000"
        )
        PortfolioStock.objects.create(
            portfolio=self.portfolio, stock=second_stock, amount="2.5000"
        )
        finnhub_service.return_value.get_stock_quote.side_effect = [
            {"c": 12.34},
            {"c": 100},
        ]

        response = self.client.get(
            reverse("portfolio_value", args=[self.portfolio.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"total": "373.400000", "currency": "USD"})
        self.assertEqual(
            finnhub_service.return_value.get_stock_quote.call_count, 2
        )

    @patch("portfolios.views.FinnhubService")
    def test_portfolio_value_reports_missing_quote(self, finnhub_service):
        stock = Stock(symbol="AAPL", company_name="Apple", exchange="NASDAQ")
        Stock.objects.bulk_create([stock])
        watchlist = Watchlist.objects.create(user=self.user, name="Tech")
        watchlist.stocks.add(stock)
        PortfolioStock.objects.create(portfolio=self.portfolio, stock=stock)
        finnhub_service.return_value.get_stock_quote.return_value = {"c": None}

        response = self.client.get(
            reverse("portfolio_value", args=[self.portfolio.pk])
        )

        self.assertEqual(response.status_code, 503)
        self.assertIn("AAPL", response.json()["error"])

    def test_portfolio_value_is_scoped_to_current_user(self):
        other_portfolio = Portfolio.objects.create(
            user=self.other_user, name="Private"
        )

        response = self.client.get(
            reverse("portfolio_value", args=[other_portfolio.pk])
        )

        self.assertEqual(response.status_code, 404)

    def test_portfolio_value_requires_login(self):
        self.client.logout()

        response = self.client.get(
            reverse("portfolio_value", args=[self.portfolio.pk])
        )

        self.assertEqual(response.status_code, 302)

    def test_empty_portfolio_value_is_zero_without_market_data_call(self):
        with patch("portfolios.views.FinnhubService") as finnhub_service:
            response = self.client.get(
                reverse("portfolio_value", args=[self.portfolio.pk])
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"total": "0", "currency": "USD"})
        finnhub_service.assert_not_called()

    def test_detail_form_offers_stocks_from_any_user_watchlist(self):
        first_stock = Stock(symbol="AAPL", company_name="Apple", exchange="NASDAQ")
        second_stock = Stock(
            symbol="MSFT", company_name="Microsoft", exchange="NASDAQ"
        )
        other_stock = Stock(symbol="GOOG", company_name="Google", exchange="NASDAQ")
        Stock.objects.bulk_create([first_stock, second_stock, other_stock])
        watched_stock = Watchlist.objects.create(user=self.user, name="Tech")
        another_watchlist = Watchlist.objects.create(
            user=self.user, name="Favorites"
        )
        watched_stock.stocks.add(first_stock)
        another_watchlist.stocks.add(second_stock)
        PortfolioStock.objects.create(
            portfolio=self.portfolio,
            stock=first_stock,
            amount="1.0000",
        )
        other_watchlist = Watchlist.objects.create(
            user=self.other_user, name="Other"
        )
        other_watchlist.stocks.add(other_stock)

        response = self.client.get(
            reverse("portfolio_detail_delete", args=[self.portfolio.pk])
        )

        choices = response.context["form"].fields["stock"].queryset
        self.assertTrue(choices.filter(pk=first_stock.pk).exists())
        self.assertTrue(choices.filter(pk=second_stock.pk).exists())
        self.assertFalse(choices.filter(pk=other_stock.pk).exists())
        self.assertContains(response, "AAPL")
        self.assertContains(response, "MSFT")
        self.assertNotContains(response, "GOOG")

    def test_update_stock_form_includes_current_holding(self):
        stock = Stock(symbol="AAPL", company_name="Apple", exchange="NASDAQ")
        other_stock = Stock(
            symbol="MSFT", company_name="Microsoft", exchange="NASDAQ"
        )
        Stock.objects.bulk_create([stock, other_stock])
        watchlist = Watchlist.objects.create(user=self.user, name="Tech")
        watchlist.stocks.add(stock, other_stock)
        PortfolioStock.objects.create(
            portfolio=self.portfolio,
            stock=stock,
            amount="1.0000",
        )
        PortfolioStock.objects.create(
            portfolio=self.portfolio,
            stock=other_stock,
            amount="2.0000",
        )

        response = self.client.get(
            reverse(
                "portfolio_update_stock",
                args=[self.portfolio.pk, stock.pk],
            )
        )

        choices = response.context["form"].fields["stock"].queryset
        self.assertTrue(choices.filter(pk=stock.pk).exists())
        self.assertFalse(choices.filter(pk=other_stock.pk).exists())
        self.assertContains(response, f'<option value="{stock.pk}" selected>')

    def test_add_stock_to_portfolio_from_watchlist(self):
        stock = Stock(symbol="AAPL", company_name="Apple", exchange="NASDAQ")
        Stock.objects.bulk_create([stock])
        watchlist = Watchlist.objects.create(user=self.user, name="Tech")
        watchlist.stocks.add(stock)

        response = self.client.post(
            reverse("portfolio_add_stock", args=[self.portfolio.pk]),
            {"stock": stock.pk, "amount": "1.2500"},
        )

        self.assertRedirects(
            response,
            reverse("portfolio_detail_delete", args=[self.portfolio.pk]),
        )
        holding = PortfolioStock.objects.get(
            portfolio=self.portfolio, stock=stock
        )
        self.assertEqual(holding.amount, 1.25)

    def test_adding_existing_stock_increases_amount_without_duplicate(self):
        stock = Stock(symbol="AAPL", company_name="Apple", exchange="NASDAQ")
        Stock.objects.bulk_create([stock])
        watchlist = Watchlist.objects.create(user=self.user, name="Tech")
        watchlist.stocks.add(stock)
        PortfolioStock.objects.create(
            portfolio=self.portfolio,
            stock=stock,
            amount="1.2500",
        )

        response = self.client.post(
            reverse("portfolio_add_stock", args=[self.portfolio.pk]),
            {"stock": stock.pk, "amount": "2.5000"},
        )

        self.assertRedirects(
            response,
            reverse("portfolio_detail_delete", args=[self.portfolio.pk]),
        )
        holdings = PortfolioStock.objects.filter(
            portfolio=self.portfolio,
            stock=stock,
        )
        self.assertEqual(holdings.count(), 1)
        self.assertEqual(holdings.get().amount, 3.75)

    def test_add_stock_rejects_stock_outside_user_watchlists(self):
        stock = Stock(symbol="MSFT", company_name="Microsoft", exchange="NASDAQ")
        Stock.objects.bulk_create([stock])
        other_watchlist = Watchlist.objects.create(
            user=self.other_user, name="Other"
        )
        other_watchlist.stocks.add(stock)

        response = self.client.post(
            reverse("portfolio_add_stock", args=[self.portfolio.pk]),
            {"stock": stock.pk, "amount": "1.0000"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Select a valid choice")
        self.assertFalse(
            PortfolioStock.objects.filter(
                portfolio=self.portfolio, stock=stock
            ).exists()
        )

    def test_add_stock_is_scoped_to_current_users_portfolio(self):
        other_portfolio = Portfolio.objects.create(
            user=self.other_user, name="Private"
        )

        response = self.client.post(
            reverse("portfolio_add_stock", args=[other_portfolio.pk]),
            {"amount": "1.0000"},
        )

        self.assertEqual(response.status_code, 404)

    def test_another_users_portfolio_is_not_accessible(self):
        other_portfolio = Portfolio.objects.create(
            user=self.other_user,
            name="Private",
        )

        response = self.client.get(
            reverse("portfolio_detail_delete", args=[other_portfolio.pk])
        )

        self.assertEqual(response.status_code, 404)

    def test_delete_portfolio(self):
        response = self.client.post(
            reverse("portfolio_detail_delete", args=[self.portfolio.pk])
        )

        self.assertRedirects(response, reverse("portfolios"))
        self.assertFalse(Portfolio.objects.filter(pk=self.portfolio.pk).exists())


class PortfolioAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='portfolio-api-user')
        cls.other_user = User.objects.create_user(username='other-api-user')
        cls.stock = Stock(symbol='AAPL', company_name='Apple', exchange='NASDAQ')
        cls.unwatched_stock = Stock(
            symbol='MSFT', company_name='Microsoft', exchange='NASDAQ'
        )
        Stock.objects.bulk_create([cls.stock, cls.unwatched_stock])
        cls.portfolio = Portfolio.objects.create(user=cls.user, name='My portfolio')
        cls.other_portfolio = Portfolio.objects.create(
            user=cls.other_user, name='Other portfolio'
        )

    def setUp(self):
        self.client.force_authenticate(user=self.user)

    def test_list_only_returns_current_users_portfolios(self):
        response = self.client.get(reverse('portfolio-list'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], self.portfolio.pk)

    def test_create_sets_current_user(self):
        response = self.client.post(
            reverse('portfolio-list'),
            {'name': 'Retirement'},
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        portfolio = Portfolio.objects.get(pk=response.data['id'])
        self.assertEqual(portfolio.user, self.user)

    def test_detail_does_not_expose_another_users_portfolio(self):
        response = self.client.get(
            reverse('portfolio-detail', args=[self.other_portfolio.pk])
        )

        self.assertEqual(response.status_code, 404)

    def test_add_stock_requires_membership_in_users_watchlist(self):
        response = self.client.post(
            reverse('portfolio-add-stock', args=[self.portfolio.pk]),
            {'symbol': self.unwatched_stock.symbol, 'amount': '1.0000'},
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(
            self.portfolio.stocks.filter(pk=self.unwatched_stock.pk).exists()
        )

    def test_add_and_remove_watchlisted_stock(self):
        watchlist = Watchlist.objects.create(user=self.user, name='Tech')
        watchlist.stocks.add(self.stock)

        add_response = self.client.post(
            reverse('portfolio-add-stock', args=[self.portfolio.pk]),
            {'symbol': ' aapl ', 'amount': '1.2500'},
            format='json',
        )

        self.assertEqual(add_response.status_code, 200)
        self.assertTrue(self.portfolio.stocks.filter(pk=self.stock.pk).exists())
        self.assertEqual(add_response.data['stock']['amount'], '1.2500')
        portfolio_stock = PortfolioStock.objects.get(
            portfolio=self.portfolio,
            stock=self.stock,
        )
        self.assertEqual(portfolio_stock.amount, 1.25)

        detail_response = self.client.get(
            reverse('portfolio-detail', args=[self.portfolio.pk])
        )
        self.assertEqual(detail_response.data['stocks'][0]['amount'], '1.2500')

        update_response = self.client.post(
            reverse('portfolio-add-stock', args=[self.portfolio.pk]),
            {'symbol': 'AAPL', 'amount': '2.5000'},
            format='json',
        )
        self.assertEqual(update_response.status_code, 200)
        portfolio_stock.refresh_from_db()
        self.assertEqual(portfolio_stock.amount, 3.75)

        remove_response = self.client.delete(
            reverse(
                'portfolio-remove-stock',
                args=[self.portfolio.pk, self.stock.symbol],
            )
        )

        self.assertEqual(remove_response.status_code, 204)
        self.assertFalse(self.portfolio.stocks.filter(pk=self.stock.pk).exists())

    def test_add_stock_rejects_non_positive_amount(self):
        response = self.client.post(
            reverse('portfolio-add-stock', args=[self.portfolio.pk]),
            {'symbol': 'AAPL', 'amount': '0'},
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(self.portfolio.stocks.filter(pk=self.stock.pk).exists())

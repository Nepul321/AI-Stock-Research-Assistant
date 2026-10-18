from django.test import TestCase
from unittest.mock import patch

from django.contrib.auth.models import User
from django.urls import reverse

from stocks.models import Stock
from watchlists.models import Watchlist


class StockDetailViewTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(
			username="stock-detail-user",
			password="Stock-detail-password-42!",
		)
		self.stock = Stock(
			symbol="NVDA",
			company_name="NVIDIA Corporation",
			exchange="NASDAQ",
		)
		Stock.objects.bulk_create([self.stock])
		self.client.force_login(self.user)

	@patch("stocks.views.FinnhubService")
	def test_detail_renders_saved_stock_and_finnhub_data(self, finnhub_class):
		finnhub = finnhub_class.return_value
		finnhub.get_stock_profile.return_value = {
			"name": "NVIDIA Corporation",
			"country": "US",
			"currency": "USD",
			"finnhubIndustry": "Semiconductors",
			"marketCapitalization": 3240000,
			"weburl": "https://www.nvidia.com/",
		}
		finnhub.get_stock_quote.return_value = {
			"c": 12345.5,
			"d": 2.1,
			"dp": 1.77,
			"h": 122.0,
			"l": 118.0,
			"o": 119.0,
			"pc": 118.4,
		}

		response = self.client.get(
			reverse("stock_detail", kwargs={"pk": self.stock.pk})
		)

		self.assertEqual(response.status_code, 200)
		self.assertTemplateUsed(response, "stocks/detail.html")
		self.assertContains(response, "NVIDIA Corporation")
		self.assertContains(response, "Semiconductors")
		self.assertContains(response, "USD 12,345.50")
		self.assertContains(response, "USD 3,240,000 million")

	@patch("base.views.FinnhubService")
	def test_dashboard_stock_listings_link_to_detail(self, finnhub_class):
		watchlist = Watchlist.objects.create(user=self.user, name="Tech")
		watchlist.stocks.add(self.stock)
		finnhub_class.return_value.get_stock_quote.return_value = {"c": 12345.5}

		response = self.client.get(reverse("home"))

		detail_url = reverse("stock_detail", kwargs={"pk": self.stock.pk})
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.content.decode().count(detail_url), 3)
		self.assertContains(response, "$12,345.50")

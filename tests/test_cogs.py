import unittest
from decimal import Decimal
from unittest.mock import patch

from src.ac_api_client import ACAPIClient
from src.cogs import calculate_cogs_for_company


class TestCOGSCalculation(unittest.TestCase):
    def setUp(self):
        self.client = ACAPIClient("http://example.local", "test-key")

    @patch.object(ACAPIClient, "get_balancesheet")
    @patch.object(ACAPIClient, "get_pnl")
    def test_basic_reconciliation(self, mock_get_pnl, mock_get_bs):
        # Setup balancesheet responses for current year and previous year
        # First call => current year
        # Second call => previous year
        mock_get_bs.side_effect = [
            {"inventory": 120, "capitalWorkInProgress": 10},
            {"inventory": 100, "capitalWorkInProgress": 15},
        ]

        mock_get_pnl.return_value = {"costOfRevenue": 80}

        res = calculate_cogs_for_company(self.client, "AAPL", 2023)

        data = res["data"]

        # Expected values computed manually
        self.assertEqual(data["cogs"], "80.00")
        self.assertEqual(data["reported_costOfRevenue"], "80.00")
        self.assertEqual(data["cwip_transfers"], "5.00")
        self.assertEqual(data["implied_purchases"], "95.00")
        self.assertEqual(data["reconciliation"], "0.00")

    @patch.object(ACAPIClient, "get_balancesheet")
    @patch.object(ACAPIClient, "get_pnl")
    def test_nested_shapes(self, mock_get_pnl, mock_get_bs):
        # balancesheet uses nested sections and labeled items
        mock_get_bs.side_effect = [
            {
                "sections": [
                    {"lineItems": [{"label": "Inventory", "amount": "(1,200)"}]},
                    {"lineItems": [{"name": "CapitalWorkInProgress", "value": "300"}]},
                ]
            },
            {
                "sections": [
                    {"lineItems": [{"label": "Inventory", "amount": "1,000"}]},
                    {"lineItems": [{"name": "CapitalWorkInProgress", "value": "350"}]},
                ]
            },
        ]

        mock_get_pnl.return_value = {"metrics": [{"name": "CostOfRevenue", "value": "150"}]}

        res = calculate_cogs_for_company(self.client, "AAPL", 2023)
        data = res["data"]

        # CWIP transfers = 350 - 300 = 50 (opening - closing -> here opening: previous year 350, closing: current 300)
        # opening inventory = 1000, closing inventory = -1200 (parentheses -> negative)
        # implied purchases = costOfRevenue - opening_inventory - cwip_transfers + closing_inventory
        # = 150 - 1000 - 50 + (-1200) = -2100
        # cogs = opening + purchases + cwip_transfers - closing = 1000 + (-2100) + 50 - (-1200) = 150
        self.assertEqual(data["cogs"], "150.00")

    @patch.object(ACAPIClient, "get_balancesheet")
    @patch.object(ACAPIClient, "get_pnl")
    def test_rounding_behavior(self, mock_get_pnl, mock_get_bs):
        mock_get_bs.side_effect = [
            {"inventory": "120.67", "capitalWorkInProgress": "10.123"},
            {"inventory": "100.12", "capitalWorkInProgress": "15.876"},
        ]

        mock_get_pnl.return_value = {"costOfRevenue": "80.555"}

        res = calculate_cogs_for_company(self.client, "AAPL", 2023)
        data = res["data"]

        # 80.555 should round HALF_UP to 80.56
        self.assertEqual(data["cogs"], "80.56")
        self.assertEqual(data["reported_costOfRevenue"], "80.56")
        # implied purchases 95.352 -> 95.35
        self.assertEqual(data["implied_purchases"], "95.35")


if __name__ == "__main__":
    unittest.main()

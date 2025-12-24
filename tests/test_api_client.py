import unittest
from unittest.mock import patch
import requests

from src.ac_api_client import ACAPIClient


class TestAPIClientErrors(unittest.TestCase):
    @patch("src.ac_api_client.requests.get")
    def test_get_balancesheet_handles_request_exception(self, mock_get):
        mock_get.side_effect = requests.RequestException("network failure")
        client = ACAPIClient("http://example.local", api_key="k")
        res = client.get_balancesheet("AAPL", 2023)
        self.assertIsInstance(res, dict)
        self.assertTrue(res.get("error"))
        self.assertIn("network failure", res.get("message"))

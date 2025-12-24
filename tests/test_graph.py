import unittest
from unittest.mock import patch

from src.ac_api_client import ACAPIClient
from src.graph import StateGraph


class TestStateGraph(unittest.TestCase):
    @patch.object(ACAPIClient, "get_balancesheet")
    @patch.object(ACAPIClient, "get_pnl")
    def test_graph_run(self, mock_get_pnl, mock_get_bs):
        mock_get_bs.side_effect = [
            {"inventory": 120, "capitalWorkInProgress": 10},
            {"inventory": 100, "capitalWorkInProgress": 15},
        ]
        mock_get_pnl.return_value = {"costOfRevenue": 80}

        client = ACAPIClient("http://example.local", api_key="test")
        graph = StateGraph(client)
        state = graph.run("AAPL", 2023)

        self.assertIn("final_report", state)
        fr = state["final_report"]
        self.assertEqual(fr["company"], "AAPL")
        self.assertEqual(fr["year"], 2023)
        self.assertIn("report", fr)

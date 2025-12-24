import json
import os
import sys

# Ensure project root is on sys.path so `src` package imports work when running the script directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ac_api_client import ACAPIClient
from src.graph import StateGraph


def run_demo():
    # Create a client (won't actually call a real server because we mock responses below)
    client = ACAPIClient("http://localhost:3000", api_key="demo-key")

    # Mocked balancesheet responses: current year and prior year
    def mock_get_balancesheet(company: str, year: int):
        if year == 2023:
            return {
                "sections": [
                    {"lineItems": [{"label": "Inventory", "amount": "1200"}]},
                    {"lineItems": [{"name": "CapitalWorkInProgress", "value": "50"}]},
                ]
            }
        if year == 2022:
            return {
                "sections": [
                    {"lineItems": [{"label": "Inventory", "amount": "1000"}]},
                    {"lineItems": [{"name": "CapitalWorkInProgress", "value": "100"}]},
                ]
            }
        return {}

    def mock_get_pnl(company: str, year: int):
        return {"metrics": [{"name": "CostOfRevenue", "value": "1100"}]}

    # Attach mocks
    client.get_balancesheet = mock_get_balancesheet
    client.get_pnl = mock_get_pnl

    graph = StateGraph(client)
    state = graph.run("AAPL", 2023)

    print(json.dumps(state.get("final_report", {}), indent=2))


if __name__ == "__main__":
    run_demo()

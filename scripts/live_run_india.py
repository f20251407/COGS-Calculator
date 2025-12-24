import json
import os
import sys

# Ensure project root is on sys.path so `src` package imports work when running the script directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ac_api_client import ACAPIClient
from src.graph import StateGraph


def run_live(company: str = "RELIANCE", year: int = 2023):
    base = os.getenv("AC_BASE_URL", "http://localhost:3000")
    client = ACAPIClient(base)

    # Health check
    health = client._get("/health")
    print("Health check:", json.dumps(health, indent=2))

    graph = StateGraph(client)
    state = graph.run(company, year)
    print("Final report:")
    print(json.dumps(state.get("final_report", {}), indent=2))


if __name__ == "__main__":
    run_live()

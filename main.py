import os
import json

from src.ac_api_client import ACAPIClient
from src.graph import StateGraph


def main(company: str = "AAPL", year: int = 2023, base_url: str | None = None):
    base = base_url or os.getenv("AC_BASE_URL", "http://localhost:3000")
    client = ACAPIClient(base)
    graph = StateGraph(client)
    state = graph.run(company, year)
    return state


if __name__ == "__main__":
    result = main()
    # Print final report as JSON for CLI use
    print(json.dumps(result.get("final_report", {}), indent=2))

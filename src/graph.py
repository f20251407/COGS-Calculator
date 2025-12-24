from typing import TypedDict, Optional, List, Dict

from .ac_api_client import ACAPIClient
from .models import FinancialState
from .cogs import calculate_cogs_for_company


class State(TypedDict, total=False):
    company: str
    year: int
    financial_data: Optional[FinancialState]
    logs: List[str]
    raw_balancesheet_current: Dict
    raw_balancesheet_prior: Dict
    raw_pnl: Dict
    report: Dict
    final_report: Dict


class StateGraph:
    def __init__(self, client: ACAPIClient):
        self.client = client

    def fetch_node(self, state: State) -> State:
        company = state["company"]
        year = state["year"]
        logs = state.get("logs", [])

        bs_current = self.client.get_balancesheet(company, year)
        if isinstance(bs_current, dict) and bs_current.get("error"):
            logs.append(f"balancesheet(current) error: {bs_current.get('message')}")

        bs_prior = self.client.get_balancesheet(company, year - 1)
        if isinstance(bs_prior, dict) and bs_prior.get("error"):
            logs.append(f"balancesheet(prior) error: {bs_prior.get('message')}")

        pnl = self.client.get_pnl(company, year)
        if isinstance(pnl, dict) and pnl.get("error"):
            logs.append(f"pnl error: {pnl.get('message')}")

        state["raw_balancesheet_current"] = bs_current
        state["raw_balancesheet_prior"] = bs_prior
        state["raw_pnl"] = pnl
        state["logs"] = logs
        return state

    def calculate_node(self, state: State) -> State:
        company = state["company"]
        year = state["year"]
        logs = state.get("logs", [])

        # Use existing calculation orchestration; prefer any previously fetched raw data
        bs_current = state.get("raw_balancesheet_current")
        bs_prior = state.get("raw_balancesheet_prior")
        pnl = state.get("raw_pnl")

        # calculate_cogs_for_company internally builds its financial state; we pass the raw data
        # by calling build_financial_state through calculate_cogs_for_company's expected flow.
        # To avoid changing calculate_cogs_for_company signature, we call build_financial_state
        # directly to get the FinancialState and then reuse calculate_cogs_for_company for final assembly.
        from .cogs import build_financial_state, compute_cwip_transfers, compute_implied_purchases, compute_cogs_from_formula

        fin_res = build_financial_state(self.client, company, year, bs_current=bs_current, bs_prev=bs_prior, pnl_current=pnl)
        fin = fin_res.get("data")

        cwip_res = compute_cwip_transfers(fin)
        purchases_res = compute_implied_purchases(fin)
        cogs_res = compute_cogs_from_formula(fin.opening_inventory, purchases_res["data"], cwip_res["data"], fin.closing_inventory)

        # Reconstruct final using the same format as calculate_cogs_for_company
        # Format numeric fields to 2 decimals (ROUND_HALF_UP) to match main calculation output
        from decimal import Decimal, ROUND_HALF_UP

        def _fmt(v):
            if not isinstance(v, Decimal):
                v = Decimal(str(v))
            return str(v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

        calc_data = {
            "cogs": _fmt(cogs_res["data"]),
            "reported_costOfRevenue": _fmt(fin.cost_of_revenue),
            "implied_purchases": _fmt(purchases_res["data"]),
            "cwip_transfers": _fmt(cwip_res["data"]),
            "reconciliation": _fmt(cogs_res["data"] - fin.cost_of_revenue),
        }

        state["report"] = calc_data
        logs.append(fin_res.get("audit_trail", ""))
        logs.append(cwip_res.get("audit_trail", ""))
        logs.append(purchases_res.get("audit_trail", ""))
        logs.append(cogs_res.get("audit_trail", ""))
        state["logs"] = logs
        return state

    def audit_node(self, state: State) -> State:
        logs = state.get("logs", [])
        report = state.get("report", {})
        final = {
            "company": state.get("company"),
            "year": state.get("year"),
            "report": report,
            "logs": logs,
        }
        state["final_report"] = final
        return state

    def run(self, company: str, year: int) -> State:
        state: State = {"company": company, "year": year, "logs": []}
        state = self.fetch_node(state)
        state = self.calculate_node(state)
        state = self.audit_node(state)
        return state

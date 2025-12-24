from decimal import Decimal, getcontext, ROUND_HALF_UP
from typing import Tuple

from .models import FinancialState
from .ac_api_client import ACAPIClient


getcontext().prec = 28


import re


def _normalize_name(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _extract_numeric(val):
    """Try to clean common number formats and return either Decimal-friendly string or numeric types unchanged."""
    if val is None:
        return None
    # If it's already numeric, return as-is
    if isinstance(val, (int, float)):
        return val
    if isinstance(val, str):
        v = val.strip()
        # handle parentheses as negative numbers: (1,234.56)
        negative = False
        if v.startswith("(") and v.endswith(")"):
            negative = True
            v = v[1:-1].strip()
        # remove commas and other non-numeric chars except dot and minus
        v = re.sub(r"[^0-9.\-]", "", v)
        if v == "":
            return None
        if negative:
            v = f"-{v}"
        return v
    return val


def _find_value(obj, key: str):
    """Robust search for a value in nested structures.

    Supports:
    - direct dict key match (case-insensitive, normalized)
    - dicts with labelled entries: {'name'/'label': <k>, 'value'/'amount': <v>}
    - lists of dicts where items use labels
    - simple coercion of string numbers (commas, parentheses)
    Returns the raw numeric/scalar value (not Decimal).
    """
    if obj is None:
        return None

    target = _normalize_name(key)
    # possible synonym candidates
    synonyms = {
        "inventory": ["inventory", "inventories", "inventorytotal", "totalinventory"],
        "capitalworkinprogress": ["capitalworkinprogress", "cwip", "workinprogress"],
        "costofrevenue": ["costofrevenue", "costofsales", "cogs", "costofgoodsold"],
    }

    candidate_names = synonyms.get(target, [key])
    candidate_norms = set(_normalize_name(x) for x in candidate_names)

    # dict handling
    if isinstance(obj, dict):
        for k, v in obj.items():
            if _normalize_name(k) in candidate_norms:
                return _extract_numeric(v)
            # check labeled entry patterns
            if isinstance(v, dict):
                name = v.get("name") or v.get("label")
                value = v.get("value") or v.get("amount") or v.get("quantity")
                if name and _normalize_name(str(name)) in candidate_norms:
                    return _extract_numeric(value)
                # recurse
                res = _find_value(v, key)
                if res is not None:
                    return res
            elif isinstance(v, list):
                res = _find_value(v, key)
                if res is not None:
                    return res

    # list handling
    if isinstance(obj, list):
        for item in obj:
            # item might be a dict with 'name'/'label' and 'value'/'amount'
            if isinstance(item, dict):
                name = item.get("name") or item.get("label")
                value = item.get("value") or item.get("amount") or item.get("quantity")
                if name and _normalize_name(str(name)) in candidate_norms:
                    return _extract_numeric(value)
            res = _find_value(item, key)
            if res is not None:
                return res

    # fallback: if scalar equals key (rare), return None
    return None


def build_financial_state(client: ACAPIClient, company: str, calendarYear: int, bs_current=None, bs_prev=None, pnl_current=None) -> dict:
    """Fetch balancesheets for year and year-1 and pnl for year and return FinancialState.

    If bs_current, bs_prev, or pnl_current are provided, they will be used instead of calling the client again.
    """
    bs_current = bs_current if bs_current is not None else client.get_balancesheet(company, calendarYear)
    bs_prev = bs_prev if bs_prev is not None else client.get_balancesheet(company, calendarYear - 1)
    pnl_current = pnl_current if pnl_current is not None else client.get_pnl(company, calendarYear)

    closing_inventory_raw = _find_value(bs_current, "inventory")
    opening_inventory_raw = _find_value(bs_prev, "inventory")

    cwip_closing_raw = _find_value(bs_current, "capitalWorkInProgress")
    cwip_opening_raw = _find_value(bs_prev, "capitalWorkInProgress")

    cost_of_revenue_raw = _find_value(pnl_current, "costOfRevenue")

    # Coerce to Decimal via FinancialState validator
    fs = FinancialState(
        opening_inventory=opening_inventory_raw or 0,
        closing_inventory=closing_inventory_raw or 0,
        cwip_opening=cwip_opening_raw or 0,
        cwip_closing=cwip_closing_raw or 0,
        cost_of_revenue=cost_of_revenue_raw or 0,
    )

    audit = (
        f"Fetched balancesheet for {company} {calendarYear} and {calendarYear -1}. "
        f"Opening inventory={fs.opening_inventory}, Closing inventory={fs.closing_inventory}, "
        f"CWIP opening={fs.cwip_opening}, CWIP closing={fs.cwip_closing}. "
        f"Fetched P&L costOfRevenue={fs.cost_of_revenue}."
    )

    return {"data": fs, "audit_trail": audit}


def compute_cwip_transfers(fin: FinancialState) -> dict:
    """CWIP Transfers are treated as opening CWIP minus closing CWIP (positive means transferred into inventory)."""
    transfers = fin.cwip_opening - fin.cwip_closing
    audit = (
        f"CWIP transfers = cwip_opening ({fin.cwip_opening}) - cwip_closing ({fin.cwip_closing}) = {transfers}"
    )
    return {"data": transfers, "audit_trail": audit}


def compute_implied_purchases(fin: FinancialState) -> dict:
    """Imply purchases using the provided costOfRevenue (COGS) and inventory/CWIP changes:
    purchases = costOfRevenue - opening_inventory - cwip_transfers + closing_inventory
    This solves for purchases when only costOfRevenue is provided.
    """
    cwip_transfers = fin.cwip_opening - fin.cwip_closing
    purchases = fin.cost_of_revenue - fin.opening_inventory - cwip_transfers + fin.closing_inventory
    audit = (
        f"Implied purchases = costOfRevenue ({fin.cost_of_revenue}) - opening_inventory ({fin.opening_inventory}) - "
        f"cwip_transfers ({cwip_transfers}) + closing_inventory ({fin.closing_inventory}) = {purchases}"
    )
    return {"data": purchases, "audit_trail": audit}


def compute_cogs_from_formula(opening: Decimal, purchases: Decimal, cwip_transfers: Decimal, closing: Decimal) -> dict:
    cogs = opening + purchases + cwip_transfers - closing
    audit = (
        f"COGS = opening_inventory ({opening}) + purchases ({purchases}) + cwip_transfers ({cwip_transfers}) - closing_inventory ({closing}) = {cogs}"
    )
    return {"data": cogs, "audit_trail": audit}


def calculate_cogs_for_company(client: ACAPIClient, company: str, calendarYear: int) -> dict:
    """Aggregate API calls and return final structured result. Returns JSON-ready dict."""
    fin_res = build_financial_state(client, company, calendarYear)
    fin: FinancialState = fin_res["data"]

    cwip_res = compute_cwip_transfers(fin)
    purchases_res = compute_implied_purchases(fin)
    cogs_res = compute_cogs_from_formula(
        fin.opening_inventory, purchases_res["data"], cwip_res["data"], fin.closing_inventory
    )

    # reconcile cogs with reported costOfRevenue
    reconciliation = cogs_res["data"] - fin.cost_of_revenue

    audit_lines = [
        fin_res["audit_trail"],
        cwip_res["audit_trail"],
        purchases_res["audit_trail"],
        cogs_res["audit_trail"],
        f"Reconciliation (calculated COGS - reported costOfRevenue) = {reconciliation}",
    ]

    # Return decimal values as strings to be JSON-ready
    def _format_currency(value: Decimal) -> str:
        # Ensure value is Decimal
        if not isinstance(value, Decimal):
            value = Decimal(str(value))
        return str(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    final = {
        "cogs": _format_currency(cogs_res["data"]),
        "reported_costOfRevenue": _format_currency(fin.cost_of_revenue),
        "implied_purchases": _format_currency(purchases_res["data"]),
        "cwip_transfers": _format_currency(cwip_res["data"]),
        "reconciliation": _format_currency(reconciliation),
    }

    return {"data": final, "audit_trail": " | ".join(audit_lines)}

# COGS Tool

Simple, precise COGS calculator that fetches financial fields from the AC_API_SERVER and computes Cost of Goods Sold in a way that is easy to audit.

---

## What this tool does ??

- Connects to the AC_API_SERVER and downloads a company's **balance sheet** and **profit & loss (P&L)** for a given year.  
- Pulls the numbers we need: **Inventory**, **Capital Work In Progress (CWIP)**, and **Cost of Revenue**.  
- Uses a simple, standard accounting formula to return a clear COGS number plus an **audit trail** that explains every step.

---

## Why use it? 💡

- Reproducible: every result comes with an `audit_trail` string that explains the arithmetic used.  
- Precise: all math uses Python's `decimal` module to avoid rounding surprises.  
- Robust: works with a variety of nested API response shapes (labels, lists, common synonyms like `cogs`, `costOfSales`, `cwip`).

---

## Quickstart — Setup (PowerShell)

1. Create & activate a virtual environment:

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
```

2. Install required packages:

```powershell
pip install pydantic requests
```

3. Run tests to confirm everything is working:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_cogs
```

---

## How it works (simple version) 🔍

1. We fetch the balance sheet for the requested year and the previous year. The previous year gives us **opening inventory**, the requested year gives **closing inventory**.
2. We fetch **costOfRevenue** from the P&L for that year.
3. We treat CWIP as an extra cost layer and compute transfers between opening and closing CWIP.
4. Because the API does not always provide a direct `purchases` number, we **imply purchases** from the reported `costOfRevenue` using the relationship in the formula below.

Formula used:

```
COGS = Opening Inventory + Purchases + CWIP Transfers - Closing Inventory
```

Where Purchases are implied as:

```
Purchases = CostOfRevenue - Opening Inventory - CWIP Transfers + Closing Inventory
```

The tool performs these calculations using Decimals and returns the final number and a reconciliation line that compares the computed COGS to the reported `costOfRevenue`.

---

## Output format (what you get back)

All functions return dictionaries with two keys: `data` and `audit_trail`.

- `data` contains the numeric results (strings of decimal values to be JSON-friendly). Example:

```json
{
	"cogs": "150.00",
	"reported_costOfRevenue": "150.00",
	"implied_purchases": "95.00",
	"cwip_transfers": "5.00",
	"reconciliation": "0.00"
}
```

- `audit_trail` is a single string describing each step (fetched fields, intermediate math, final reconciliation).

---

## Example (Python)

```py
from src.ac_api_client import ACAPIClient
from src.cogs import calculate_cogs_for_company

client = ACAPIClient("http://localhost:3000", api_key="YOUR_API_KEY")
result = calculate_cogs_for_company(client, "AAPL", 2023)
# handle result['data'] and result['audit_trail'] programmatically — functions return values (no printing inside)
```

Notes:
- Replace `http://localhost:3000` with your server base URL.
- The client sends the API key in the header `x-api-key`.

---

## Assumptions & Limitations ⚠️

- If the API omits a value, it is treated as zero (safe default).  
- The tool infers purchases when they are not provided by the API; if you have a direct `purchases` field available, you can wire it in to replace the implied calculation.  
- The parser is robust but may still miss extremely unusual response formats; feel free to open an issue with a sample payload and I can extend the pattern matching.

---

## Testing

Run unit tests that mock API responses and validate calculations:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_cogs
```

---

## Contributing

Contributions are welcome. Please follow the existing code style (Pydantic models, Decimal math, no print statements — functions must return values). Add unit tests for new cases.

---

## License

This repository includes a `LICENSE` file; reuse accordingly.


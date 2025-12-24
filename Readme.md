# COGS Tool

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Simple, precise Cost of Goods Sold (COGS) calculator that fetches financial fields from an AC API server and returns a reproducible, auditable COGS calculation for a company and year.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Quickstart](#quickstart)
- [Configuration (.env)](#configuration-env)
- [Usage](#usage)
  - [Python API example](#python-api-example)
  - [Demo scripts](#demo-scripts)
- [How it works](#how-it-works)
- [Output format](#output-format)
- [Testing](#testing)
- [Contributing](#contributing)
- [Project structure](#project-structure)
- [License](#license)

---

## Overview

This project provides a deterministic calculation of COGS using values pulled from a financial AC API. It focuses on correctness (use of Python's `decimal`), clarity (an `audit_trail` describing the arithmetic), and flexible parsing of API payloads.

### Features

- Fetches balance sheet and profit & loss for a company and year
- Infers missing `purchases` from `costOfRevenue` when needed
- Includes CWIP handling and reconciliation output
- Returns results with a human-readable `audit_trail` for traceability

---

## Quickstart

These steps get the project running locally for development and testing.

1. Clone the repo (already done if you are working locally):

```bash
git clone https://github.com/f20251407/COGS-Calculator.git
cd COGS-Calculator
```

2. Create and activate a virtual environment (Windows PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Or (macOS / Linux):

```bash
python -m venv .venv
source .venv/bin/activate
```

3. Install the requirements:

```bash
pip install -r requirements.txt
```

> Tip: pin exact dependency versions in `requirements.txt` for reproducible installs.

---

## Configuration (.env)

The project reads runtime configuration from a `.env` file at the repository root. Do not check secrets into source control — `.env` is included in `.gitignore`.

Example `.env` (do not commit real secrets):

```
AC_API_KEY=your_api_key_here
AC_BASE_URL=https://api.example.com
```

- `AC_API_KEY`: API key used by `ACAPIClient` (sent as `x-api-key` header)
- `AC_BASE_URL`: Base URL for the AC server (default in this repo was `http://localhost:3000`)

---

## Usage

### Python API example

```py
from src.ac_api_client import ACAPIClient
from src.cogs import calculate_cogs_for_company

client = ACAPIClient(base_url="https://api.example.com", api_key="YOUR_API_KEY")
result = calculate_cogs_for_company(client, "AAPL", 2023)
print(result['data'])
print(result['audit_trail'])
```

`calculate_cogs_for_company` returns a dictionary with numeric values (as strings) in `data` and a verbose `audit_trail` string explaining each step.

### Demo scripts

There are example scripts in `scripts/` demonstrating how to call the module with live or mocked data:

```bash
# Run a demo example (adjust script args as needed)
python scripts/demo_real_example.py --company AAPL --year 2023

# Example: a country-specific live run
python scripts/live_run_india.py --year 2023
```

(If the scripts accept CLI args, use `--help` to view options.)

---

## How it works

At a high level, the tool:

1. Fetches balance sheet and P&L for the requested year and previous year
2. Extracts `opening_inventory`, `closing_inventory`, `costOfRevenue`, and `cwip` movements
3. Infers `purchases` when not provided, using the relationship:

```
COGS = Opening Inventory + Purchases + CWIP Transfers - Closing Inventory
```

4. Performs all calculations using the `decimal` module for exact arithmetic and returns a `reconciliation` value to indicate any difference from reported fields.

---

## Output format

Returned value example:

```json
{
  "data": {
    "cogs": "150.00",
    "reported_costOfRevenue": "150.00",
    "implied_purchases": "95.00",
    "cwip_transfers": "5.00",
    "reconciliation": "0.00"
  },
  "audit_trail": "Fetched balance_sheet.{...}; Opening inventory=...; Closing inventory=...; Computed purchases=...; Final COGS=..."
}
```

`audit_trail` is intentionally verbose; it makes results easy to audit and debug.

---

## Testing

Unit tests use Python's `unittest` and mock API responses. Run tests locally:

```bash
pytest -q
# or using unittest
python -m unittest discover -v
```

Add tests for any parsing edge cases or new calculation logic.

---

## CI / GitHub Actions

This repository can use GitHub Actions to run tests on pull requests. Consider adding a workflow (e.g., `.github/workflows/ci.yml`) that:

- Installs dependencies
- Runs the test suite
- Optionally runs linters (flake8, black)

If you'd like, I can add a sample CI workflow for you.

---

## Contributing

Thanks for contributing! A few guidelines:

- Open an issue for large changes before creating a PR
- Create a feature branch: `git checkout -b feat/your-thing`
- Add unit tests for new behavior
- Keep changes small and focused
- Ensure tests pass locally before submitting a PR

---

## Project structure

- `src/` — implementation modules (`ac_api_client.py`, `cogs.py`, `graph.py`, `models.py`)
- `scripts/` — convenient runnable examples and live-run helpers
- `tests/` — unit tests that mock the AC API responses
- `.env` — local configuration (ignored by git)

---

## License

This project is licensed under the MIT License — see `LICENSE` for details.


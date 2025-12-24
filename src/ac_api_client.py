from typing import Any, Dict, Optional
import os
from dotenv import load_dotenv
import requests


# Load .env automatically (if present)
load_dotenv()


class ACAPIClient:
    def __init__(self, base_url: str, api_key: Optional[str] = None, timeout: int = 10):
        self.base_url = base_url.rstrip("/")
        # Prefer explicit API key, otherwise fall back to environment
        self.api_key = api_key or os.getenv("AC_API_KEY")
        self.timeout = timeout

    def _get(self, path: str, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        headers = {"x-api-key": self.api_key} if self.api_key else {}
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=self.timeout)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            # Return a structured error dict instead of raising to allow graph-level handling
            return {"error": True, "message": str(exc), "status_code": getattr(getattr(exc, "response", None), "status_code", None)}

    def get_balancesheet(self, company: str, calendarYear: int | None = None) -> Dict[str, Any]:
        params = {"calendarYear": calendarYear} if calendarYear is not None else None
        return self._get(f"/server/company/balancesheet/{company}", params=params)

    def get_pnl(self, company: str, calendarYear: int | None = None) -> Dict[str, Any]:
        params = {"calendarYear": calendarYear} if calendarYear is not None else None
        return self._get(f"/server/company/pnl/{company}", params=params)

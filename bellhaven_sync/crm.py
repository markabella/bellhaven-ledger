from __future__ import annotations

from typing import Any

import requests

from .config import API_BASE, require_token


class CRMClient:
    def __init__(self, token: str | None = None, timeout: int = 20):
        self.base = API_BASE
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {"Authorization": f"Bearer {token or require_token()}", "Accept": "application/json"}
        )

    def list_accounts(self) -> list[dict[str, Any]]:
        page, accounts = 1, []
        while True:
            response = self.session.get(
                f"{self.base}/accounts",
                params={"page": page, "page_size": 50},
                timeout=self.timeout,
            )
            response.raise_for_status()
            body = response.json()
            accounts.extend(body["data"])
            if len(accounts) >= body["total"]:
                return accounts
            page += 1

    def get_account(self, account_id: str) -> dict[str, Any]:
        response = self.session.get(
            f"{self.base}/accounts/{account_id}", timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()

    def create_account(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = self.session.post(
            f"{self.base}/accounts", json=payload, timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()

    def update_account(self, account_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = self.session.patch(
            f"{self.base}/accounts/{account_id}", json=payload, timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()


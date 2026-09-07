from __future__ import annotations

import copy
from typing import Any

from .crm import CRMClient
from .matcher import reconcile
from .scraper import scrape_locations
from .store import load_state, merge_proposals, save_state, utc_now


def _created_account(result: dict[str, Any]) -> dict[str, Any]:
    """Normalize either a direct response or a ``data`` response envelope."""
    data = result.get("data")
    return data if isinstance(data, dict) else result


def _find_existing_creation(client: CRMClient, body: dict[str, Any]) -> dict[str, Any] | None:
    """Avoid a duplicate POST after an interrupted or uncertain prior attempt."""
    from .matcher import norm

    for account in client.list_accounts():
        if (
            norm(account.get("name", "")) == norm(body.get("name", ""))
            and account.get("parent_id", "") == body.get("parent_id", "")
            and norm(account.get("billing_street", "")) == norm(body.get("billing_street", ""))
            and norm(account.get("billing_city", "")) == norm(body.get("billing_city", ""))
            and str(account.get("billing_zip", ""))[:5] == str(body.get("billing_zip", ""))[:5]
        ):
            return account
    return None


def scan() -> dict[str, Any]:
    locations = scrape_locations()
    accounts = CRMClient().list_accounts()
    state = merge_proposals(reconcile(locations, accounts))
    state["source_counts"] = {"website_locations": len(locations), "crm_accounts": len(accounts)}
    save_state(state)
    return state


def _resolve(value: Any, context: dict[str, Any]) -> Any:
    if isinstance(value, str) and value.startswith("$"):
        parts = value[1:].split(".")
        result: Any = context
        for part in parts:
            result = result[part]
        return result
    if isinstance(value, dict):
        return {key: _resolve(item, context) for key, item in value.items()}
    if isinstance(value, list):
        return [_resolve(item, context) for item in value]
    return value


def apply_proposal(proposal_id: str) -> dict[str, Any]:
    state = load_state()
    proposal = next((p for p in state["proposals"] if p["id"] == proposal_id), None)
    if not proposal:
        raise KeyError(f"Unknown proposal {proposal_id}")
    if proposal["status"] != "pending":
        return proposal
    client = CRMClient()
    results = proposal.get("action_results", [])
    context: dict[str, Any] = {}
    for index, previous in enumerate(results):
        save_as = proposal["actions"][index].get("save_as")
        if save_as:
            context[save_as] = _created_account(previous)
    for index, action in enumerate(proposal["actions"]):
        if index < len(results):
            continue
        body = _resolve(copy.deepcopy(action["body"]), context)
        try:
            if action["method"] == "POST":
                result = _find_existing_creation(client, body) or client.create_account(body)
            elif action["method"] == "PATCH":
                account_id = action["path"].rsplit("/", 1)[-1]
                result = client.update_account(account_id, body)
            else:
                raise ValueError(f"Unsupported method {action['method']}")
        except Exception as exc:
            proposal["last_error"] = f"{type(exc).__name__}: {exc}"
            proposal["action_results"] = results
            save_state(state)
            raise
        result = _created_account(result)
        results.append(result)
        proposal["action_results"] = results
        proposal.pop("last_error", None)
        save_state(state)
        if action.get("save_as"):
            context[action["save_as"]] = result
    proposal.update(status="approved", decided_at=utc_now(), result=results)
    proposal.pop("action_results", None)
    save_state(state)
    return proposal


def reject_proposal(proposal_id: str) -> dict[str, Any]:
    state = load_state()
    proposal = next((p for p in state["proposals"] if p["id"] == proposal_id), None)
    if not proposal:
        raise KeyError(f"Unknown proposal {proposal_id}")
    if proposal["status"] == "pending":
        proposal.update(status="rejected", decided_at=utc_now(), result=[])
        save_state(state)
    return proposal

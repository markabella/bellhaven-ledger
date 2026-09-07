from __future__ import annotations

import hashlib
import json
import re
from difflib import SequenceMatcher
from typing import Any


PARENT_NAME = "Bellhaven Senior Living (Parent Account)"
CARE_MAP = {
    "Assisted Living": "Assisted Living",
    "Memory Support": "Memory Care",
    "Short-Term Rehabilitation & Nursing": "Skilled Nursing",
}
STREET_WORDS = {
    "avenue": "ave", "boulevard": "blvd", "drive": "dr", "lane": "ln",
    "road": "rd", "street": "st", "north": "n", "south": "s",
    "east": "e", "west": "w", "northwest": "nw", "northeast": "ne",
    "southwest": "sw", "southeast": "se", "centre": "center",
}


def norm(value: str) -> str:
    value = value.casefold().replace("&", " and ")
    words = re.findall(r"[a-z0-9]+", value)
    return " ".join(STREET_WORDS.get(word, word) for word in words)


def digits(value: str) -> str:
    return "".join(re.findall(r"\d", value or ""))


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, norm(a), norm(b)).ratio()


def desired_care(location: dict) -> str:
    return "; ".join(CARE_MAP.get(item, item) for item in location["care_offerings"])


def account_snapshot(account: dict) -> dict:
    keys = [
        "account_id", "name", "parent_id", "parent_name", "billing_street",
        "billing_city", "billing_state", "billing_zip", "care_type", "status",
        "phone", "lifetime_revenue", "outstanding_ar", "chow_current_account",
        "duplicate_of_account", "note",
    ]
    return {key: account.get(key, "") for key in keys}


def proposal_id(kind: str, key: str, actions: list[dict]) -> str:
    raw = json.dumps([kind, key, actions], sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()[:14]


def make_proposal(kind: str, key: str, title: str, summary: str, confidence: int,
                  evidence: list[str], website: dict | None, crm: list[dict], actions: list[dict]) -> dict:
    return {
        "id": proposal_id(kind, key, actions), "kind": kind, "title": title,
        "summary": summary, "confidence": confidence, "evidence": evidence,
        "website": website, "crm": [account_snapshot(a) for a in crm],
        "actions": actions, "status": "pending",
    }


def _candidate_score(location: dict, account: dict) -> tuple[float, list[str]]:
    name = similarity(location["name"], account["name"])
    street = similarity(location["address"], account["billing_street"])
    city = norm(location["city"]) == norm(account["billing_city"])
    state = location["state"] == account["billing_state"]
    zipcode = location["zip"][:5] == str(account["billing_zip"])[:5]
    phone = digits(location["phone"])[-10:] == digits(account.get("phone", ""))[-10:]
    house = (re.match(r"\d+", location["address"]) or [""])[0] == (re.match(r"\d+", account["billing_street"]) or [""])[0]
    score = 0.35 * name + 0.30 * street + 0.12 * city + 0.08 * state + 0.10 * zipcode + 0.05 * phone
    if house and zipcode:
        score = max(score, 0.88 + 0.07 * name + 0.05 * street)
    # A matching facility name and locality can survive a street move or a stale PO box.
    if name >= 0.96 and city and state and zipcode:
        score = max(score, 0.95)
    evidence = [f"name {name:.0%}", f"street {street:.0%}"]
    evidence += [label for flag, label in ((zipcode, "ZIP exact"), (city and state, "city/state exact"), (phone, "phone exact")) if flag]
    return score, evidence


def _desired_fields(location: dict, parent_id: str) -> dict:
    return {
        "name": location["name"], "parent_id": parent_id,
        "billing_street": location["address"], "billing_city": location["city"],
        "billing_state": location["state"], "billing_zip": location["zip"],
        "care_type": desired_care(location), "status": "Active",
    }


def reconcile(locations: list[dict], accounts: list[dict]) -> list[dict]:
    parent = next(a for a in accounts if a["name"] == PARENT_NAME)
    parent_id = parent["account_id"]
    proposals: list[dict] = []
    matched_ids: set[str] = set()

    for location in locations:
        ranked = sorted(
            (
                (_candidate_score(location, account), account)
                for account in accounts
                if account["account_id"] != parent_id
                and not account.get("duplicate_of_account")
                and not account.get("chow_current_account")
            ),
            key=lambda item: item[0][0], reverse=True,
        )
        (best_score, evidence), best = ranked[0]
        credible = [(score, ev, acc) for (score, ev), acc in ranked if score >= 0.82]
        desired = _desired_fields(location, parent_id)

        if best_score < 0.82:
            actions = [{"method": "POST", "path": "/accounts", "body": desired}]
            proposals.append(make_proposal(
                "create", location["source_url"], f"Create {location['name']}",
                "No credible CRM account exists for this website location.", 93,
                evidence + [f"best candidate score {best_score:.0%}"], location, [], actions,
            ))
            continue

        # Exact-location duplicates are grouped behind the strongest survivor.
        same_site = [item for item in credible if item[2]["billing_zip"] == best["billing_zip"] and similarity(item[2]["billing_street"], best["billing_street"]) >= 0.88]
        survivor = best
        if len(same_site) > 1:
            same_site.sort(key=lambda item: (digits(item[2].get("phone", ""))[-10:] == digits(location["phone"])[-10:], item[0]), reverse=True)
            _, evidence, survivor = same_site[0]
            best_score = same_site[0][0]
        matched_ids.add(survivor["account_id"])

        patch = {}
        for key, value in desired.items():
            old_value = survivor.get(key, "")
            # Avoid churn between equivalent postal abbreviations while still fixing
            # substantively wrong streets.
            if key == "billing_street" and norm(str(old_value)) == norm(str(value)):
                continue
            if str(old_value) != str(value):
                patch[key] = value
        wrong_parent = survivor.get("parent_id") != parent_id
        has_protected_ar = float(survivor.get("lifetime_revenue") or 0) > 0 and float(survivor.get("outstanding_ar") or 0) > 0

        if wrong_parent and has_protected_ar:
            create_body = dict(desired)
            create_body["phone"] = location["phone"]
            create_body["note"] = f"Created for CHOW from legacy account {survivor['account_id']}; website verified."
            actions = [
                {"method": "POST", "path": "/accounts", "body": create_body, "save_as": "new_account"},
                {"method": "PATCH", "path": f"/accounts/{survivor['account_id']}", "body": {
                    "chow_current_account": "$new_account.account_id",
                    "note": f"CHOW: billing history and outstanding AR preserved. Current operating account created for {location['name']}.",
                }},
            ]
            proposals.append(make_proposal(
                "chow", survivor["account_id"], f"Preserve billing history: {location['name']}",
                "Wrong parent, but revenue and open AR require a new current account instead of re-parenting.", 99,
                evidence + [f"lifetime revenue ${survivor['lifetime_revenue']:,.0f}", f"outstanding AR ${survivor['outstanding_ar']:,.0f}"],
                location, [survivor], actions,
            ))
        elif patch:
            kind = "reparent" if wrong_parent else "update"
            reason = "Re-parent and align fields to the website." if wrong_parent else "Align stale CRM fields to the website."
            actions = [{"method": "PATCH", "path": f"/accounts/{survivor['account_id']}", "body": patch}]
            proposals.append(make_proposal(
                kind, survivor["account_id"], f"{reason.split()[0]} {location['name']}", reason,
                min(99, round(best_score * 100)), evidence, location, [survivor], actions,
            ))

        for _, dup_evidence, duplicate in same_site[1:]:
            matched_ids.add(duplicate["account_id"])
            actions = [{"method": "PATCH", "path": f"/accounts/{duplicate['account_id']}", "body": {
                "duplicate_of_account": survivor["account_id"], "status": "Inactive",
                "note": f"Duplicate of {survivor['account_id']} ({survivor['name']}); same website-verified facility.",
            }}]
            proposals.append(make_proposal(
                "duplicate", duplicate["account_id"], f"Retire duplicate: {duplicate['name']}",
                f"Same facility as surviving account {survivor['account_id']}.", 99,
                dup_evidence, location, [survivor, duplicate], actions,
            ))

    # Bellhaven children not represented by any current website location are inactive operations.
    for account in accounts:
        if account.get("parent_id") != parent_id or account["account_id"] in matched_ids:
            continue
        if account.get("status") == "Inactive" and "website" in account.get("note", "").casefold():
            continue
        actions = [{"method": "PATCH", "path": f"/accounts/{account['account_id']}", "body": {
            "status": "Inactive",
            "note": "No longer listed on the Bellhaven website; retained for history and marked inactive by daily reconciliation.",
        }}]
        proposals.append(make_proposal(
            "stale", account["account_id"], f"Deactivate former location: {account['name']}",
            "CRM child account is absent from Bellhaven's complete public directory.", 96,
            ["under Bellhaven parent", "not among current website locations"], None, [account], actions,
        ))
    return sorted(proposals, key=lambda p: (p["kind"], p["title"]))

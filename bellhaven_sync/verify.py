from __future__ import annotations

from typing import Any

from .crm import CRMClient
from .matcher import PARENT_NAME, desired_care, norm, reconcile
from .scraper import scrape_locations


def verify_end_state() -> dict[str, Any]:
    locations = scrape_locations()
    accounts = CRMClient().list_accounts()
    by_id = {account["account_id"]: account for account in accounts}
    parent = next(account for account in accounts if account["name"] == PARENT_NAME)
    current = [
        account for account in accounts
        if account.get("parent_id") == parent["account_id"]
        and account.get("status") == "Active"
        and not account.get("duplicate_of_account")
    ]
    expected = {(norm(location["name"]), norm(location["address"]), location["zip"][:5], desired_care(location)) for location in locations}
    actual = {(norm(account["name"]), norm(account["billing_street"]), str(account["billing_zip"])[:5], account["care_type"]) for account in current}
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)

    chow_legacy = [account for account in accounts if account.get("chow_current_account")]
    broken_chow = [
        account["account_id"] for account in chow_legacy
        if account["chow_current_account"] not in by_id
        or by_id[account["chow_current_account"]].get("parent_id") != parent["account_id"]
        or not (float(account.get("lifetime_revenue") or 0) > 0 and float(account.get("outstanding_ar") or 0) > 0)
    ]
    duplicates = [account for account in accounts if account.get("duplicate_of_account")]
    broken_duplicates = [
        account["account_id"] for account in duplicates
        if account.get("status") != "Inactive" or account["duplicate_of_account"] not in by_id
    ]
    remaining = reconcile(locations, accounts)
    report = {
        "website_locations": len(locations),
        "active_bellhaven_children": len(current),
        "crm_accounts": len(accounts),
        "chow_legacy_accounts": len(chow_legacy),
        "inactive_duplicates": len(duplicates),
        "remaining_proposals": len(remaining),
        "missing_current_locations": missing,
        "extra_current_locations": extra,
        "broken_chow_links": broken_chow,
        "broken_duplicate_links": broken_duplicates,
    }
    report["ok"] = not any((missing, extra, broken_chow, broken_duplicates, remaining)) and len(current) == len(locations)
    return report


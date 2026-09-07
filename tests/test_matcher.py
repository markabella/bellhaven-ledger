from bellhaven_sync.matcher import norm, reconcile


def test_normalizes_common_street_variants():
    assert norm("4850 Northwest Sylvania Avenue") == norm("4850 NW Sylvania Ave")


def test_chow_sop_creates_then_links_old_account():
    parent = {"account_id": "P", "name": "Bellhaven Senior Living (Parent Account)"}
    old = {"account_id": "OLD", "name": "Bellhaven of Test", "parent_id": "OTHER", "parent_name": "Other", "billing_street": "10 Main St", "billing_city": "Test", "billing_state": "OH", "billing_zip": "44444", "care_type": "Skilled Nursing", "status": "Active", "phone": "555-111-2222", "lifetime_revenue": 100, "outstanding_ar": 10, "chow_current_account": "", "duplicate_of_account": "", "note": ""}
    location = {"name": "Bellhaven of Test", "address": "10 Main Street", "city": "Test", "state": "OH", "zip": "44444", "care_offerings": ["Short-Term Rehabilitation & Nursing"], "phone": "555-111-2222", "administrator": "A", "source_url": "https://example.test/test"}
    chow = next(p for p in reconcile([location], [parent, old]) if p["kind"] == "chow")
    assert [a["method"] for a in chow["actions"]] == ["POST", "PATCH"]
    assert chow["actions"][1]["body"]["chow_current_account"] == "$new_account.account_id"


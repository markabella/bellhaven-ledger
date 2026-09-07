# Bellhaven Ledger

Bellhaven Ledger reconciles Bellhaven's public community directory with a CRM sandbox. It scrapes every website location, matches with address-first evidence, presents changes for human review, and writes only approved actions. Decisions are durable: approved and rejected proposal fingerprints are not re-proposed on later runs.

## Quick start

```powershell
python -m pip install -r requirements.txt
$env:BELLHAVEN_API_TOKEN="your-token"
python manage.py scan
python app.py
```

Open `http://127.0.0.1:5000`. Review the evidence and exact API payload for each case, then approve or reject. The token is read from the environment and never stored in the repository.

The runtime ledger at `data/review_state.json` is deliberately gitignored because it can contain CRM addresses, contacts, and financial evidence. The app creates it automatically on the first scan.

## Matching strategy

The matcher ranks every CRM account using normalized name and street similarity plus exact city/state, ZIP, house number, and phone evidence. Address and ZIP dominate because names can change after an acquisition. A score below 82% becomes a create proposal. Multiple accounts at the same address become a survivor/duplicate decision, with an exact public phone match breaking ties.

For matched accounts, the public site is authoritative for name, address, care offerings, and active status. Existing Bellhaven children absent from the complete site directory are proposed as Inactive and retained with an audit note.

## CHOW safeguard

When a matched facility is under the wrong parent, the pipeline checks `lifetime_revenue` and `outstanding_ar` before proposing any write:

- Revenue history **and** open AR: preserve the old account, create a new Bellhaven child, then set `chow_current_account` on the old record.
- Otherwise: re-parent the existing account directly.

CHOW creation and linkage appear as one review case and execute in the required order.

## Safe daily operation

The included `schedule.cron` runs a scan every morning from the same persistent checkout. It does not approve changes. Stable proposal fingerprints and the durable JSON decision ledger make scans idempotent, while the current CRM state naturally suppresses already-applied field corrections.

## Tests

```powershell
python -m pytest -q
```

Tests cover address normalization and the financially protected CHOW branch. No test writes to the CRM.

After approvals, `python manage.py verify` compares all current Bellhaven children to the website and validates CHOW and duplicate links. It exits non-zero if any mismatch or new proposal remains.

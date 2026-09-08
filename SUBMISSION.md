# Clipboard Analyst Assessment — Submission

## Submission timeline

- Workspace created: Sep 7, 2026, 5:39 PM CDT
- Submission deadline: Sep 9, 2026, 5:39 PM CDT
- Submitted: Sep 7, 2026, 6:54 PM CDT

## Repository link

[Public GitHub repository](https://github.com/markabella/bellhaven-ledger). The packaged `bellhaven-ledger.zip` is also stored in Google Drive.

## Actual time spent

0.8 hours of active work within a 1 hour 15 minute workspace window (AI-assisted implementation, data review, CRM correction, and verification).

## Write-up

I treated the website as the source of truth for the current operating roster and used address-first entity resolution because ownership changes frequently bring name changes. The matcher normalizes common postal variants, then combines name and street similarity with exact city/state, ZIP, house number, and phone evidence. Strong matches can produce field corrections or parent changes; weak matches become new-account proposals. Multiple records at the same verified address become an explicit survivor/duplicate decision. Existing Bellhaven children missing from the complete website directory are retained but marked Inactive with an audit note.

The CHOW SOP is a first-class branch, not a reviewer reminder. Before any re-parent, the pipeline checks lifetime revenue and outstanding AR. Marietta and Tiffin had both, so their historical accounts were preserved under the old parent, new Bellhaven operating accounts were created, and the old records were linked through `chow_current_account`. Other parent corrections were applied directly. Writes are checkpointed per action, and every create checks for an existing same-name/same-address account before POSTing, making interrupted retries safe.

I used Codex to scaffold the Python pipeline, challenge ambiguous matches, inspect all 29 evidence cards, and add tests and end-state assertions. I did not use an LLM in the runtime matcher: deterministic evidence is cheaper, reproducible, and easier for an operator to audit. The finished CRM has 34 active Bellhaven child accounts for 34 website locations, two valid CHOW chains, seven inactive duplicate records, and zero remaining proposals.

Next, I’d move the JSON ledger into a small transactional database.

I’d add reviewer logins and require a second approval for high-revenue CHOW cases.

I’d also save each source snapshot, so there’s a clear audit trail.

If confidence drops or the site structure changes, the system would flag it.

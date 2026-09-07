# Clipboard Analyst Assessment — Submission

## Repository link

Upload the packaged `bellhaven-ledger.zip` to a public GitHub repository or shared Drive folder, then paste that URL into the assessment form.

## Actual time spent

0.8 hours (AI-assisted implementation, data review, CRM correction, and verification).

## Write-up

I treated the website as the source of truth for the current operating roster and used address-first entity resolution because ownership changes frequently bring name changes. The matcher normalizes common postal variants, then combines name and street similarity with exact city/state, ZIP, house number, and phone evidence. Strong matches can produce field corrections or parent changes; weak matches become new-account proposals. Multiple records at the same verified address become an explicit survivor/duplicate decision. Existing Bellhaven children missing from the complete website directory are retained but marked Inactive with an audit note.

The CHOW SOP is a first-class branch, not a reviewer reminder. Before any re-parent, the pipeline checks lifetime revenue and outstanding AR. Marietta and Tiffin had both, so their historical accounts were preserved under the old parent, new Bellhaven operating accounts were created, and the old records were linked through `chow_current_account`. Other parent corrections were applied directly. Writes are checkpointed per action, and every create checks for an existing same-name/same-address account before POSTing, making interrupted retries safe.

I used Codex to scaffold the Python pipeline, challenge ambiguous matches, inspect all 29 evidence cards, and add tests and end-state assertions. I did not use an LLM in the runtime matcher: deterministic evidence is cheaper, reproducible, and easier for an operator to audit. The finished CRM has 34 active Bellhaven child accounts for 34 website locations, two valid CHOW chains, seven inactive duplicate records, and zero remaining proposals.

Next I would move the JSON ledger to a small transactional database, add authenticated reviewers and two-person approval for high-revenue CHOW cases, record source snapshots for historical audits, and emit alerts when confidence drops or the site structure changes.

from __future__ import annotations

import argparse
import json

from bellhaven_sync.pipeline import apply_proposal, reject_proposal, scan
from bellhaven_sync.store import load_state
from bellhaven_sync.verify import verify_end_state


def main() -> None:
    parser = argparse.ArgumentParser(description="Bellhaven CRM reconciliation")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("scan", help="Scrape, match, and refresh the review queue")
    sub.add_parser("status", help="Summarize the review queue")
    sub.add_parser("approve-all", help="Apply every currently pending reviewed proposal")
    sub.add_parser("verify", help="Verify the corrected CRM against the website and SOP")
    decide = sub.add_parser("decide", help="Approve or reject one proposal")
    decide.add_argument("proposal_id")
    decide.add_argument("decision", choices=["approve", "reject"])
    args = parser.parse_args()

    if args.command == "scan":
        state = scan()
    elif args.command == "status":
        state = load_state()
    elif args.command == "verify":
        report = verify_end_state()
        print(json.dumps(report, indent=2))
        raise SystemExit(0 if report["ok"] else 1)
    elif args.command == "approve-all":
        pending = [p["id"] for p in load_state().get("proposals", []) if p["status"] == "pending"]
        for number, proposal_id in enumerate(pending, 1):
            proposal = apply_proposal(proposal_id)
            print(f"[{number}/{len(pending)}] applied {proposal['kind']}: {proposal['title']}")
        return
    else:
        proposal = apply_proposal(args.proposal_id) if args.decision == "approve" else reject_proposal(args.proposal_id)
        print(json.dumps(proposal, indent=2))
        return
    counts: dict[str, int] = {}
    for proposal in state.get("proposals", []):
        key = f"{proposal['status']}:{proposal['kind']}"
        counts[key] = counts.get(key, 0) + 1
    print(json.dumps({"generated_at": state.get("generated_at"), "source_counts": state.get("source_counts"), "counts": counts}, indent=2))


if __name__ == "__main__":
    main()

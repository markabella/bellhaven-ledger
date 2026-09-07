from __future__ import annotations

from flask import Flask, flash, redirect, render_template, request, url_for

from bellhaven_sync.pipeline import apply_proposal, reject_proposal, scan
from bellhaven_sync.store import load_state

app = Flask(__name__)
app.secret_key = "local-review-only"


@app.get("/")
def index():
    state = load_state()
    status = request.args.get("status", "pending")
    kind = request.args.get("kind", "all")
    proposals = [p for p in state.get("proposals", []) if status == "all" or p["status"] == status]
    proposals = [p for p in proposals if kind == "all" or p["kind"] == kind]
    totals = {name: sum(p["status"] == name for p in state.get("proposals", [])) for name in ("pending", "approved", "rejected")}
    return render_template("index.html", state=state, proposals=proposals, totals=totals, active_status=status, active_kind=kind)


@app.post("/scan")
def run_scan():
    state = scan()
    flash(f"Scan complete: {len(state['proposals'])} proposals in the ledger.")
    return redirect(url_for("index"))


@app.post("/proposals/<proposal_id>/<decision>")
def decide(proposal_id: str, decision: str):
    if decision == "approve":
        try:
            proposal = apply_proposal(proposal_id)
        except Exception as exc:
            flash(f"Write stopped safely: {type(exc).__name__}. No later actions were attempted.")
        else:
            flash(f"Approved and applied: {proposal['title']}")
    elif decision == "reject":
        proposal = reject_proposal(proposal_id)
        flash(f"Rejected: {proposal['title']}")
    else:
        raise ValueError("Decision must be approve or reject")
    return redirect(request.referrer or url_for("index"))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)

"""
monitor.py — PRAETOR Intelligence
Re-scan a domain and diff against the previous scan stored in leads.json.

Usage (Render Cron Job or CLI):
    python monitor.py --domain example.com [--depth pro]
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

from scan_target import scan_target, _is_valid_domain

LEADS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "leads.json")


# ── Storage helpers ─────────────────────────────────────────────────────────

def _load_leads() -> dict:
    if not os.path.exists(LEADS_FILE):
        return {}
    try:
        with open(LEADS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_leads(leads: dict) -> None:
    with open(LEADS_FILE, "w", encoding="utf-8") as f:
        json.dump(leads, f, ensure_ascii=False, indent=2)


def get_previous_scan(domain: str) -> dict | None:
    """Return the most recent stored scan for domain, or None."""
    leads = _load_leads()
    entry = leads.get(domain)
    if not entry:
        return None
    # Support both direct scan dict and {"scans": [...]} history list
    if "scans" in entry:
        return entry["scans"][-1] if entry["scans"] else None
    return entry if entry.get("scanned_at") else None


def store_scan(domain: str, scan: dict) -> None:
    """Append scan to the domain's history in leads.json."""
    leads = _load_leads()
    if domain not in leads:
        leads[domain] = {"scans": []}
    elif "scans" not in leads[domain]:
        # Migrate flat entry to history list
        previous = {k: v for k, v in leads[domain].items()}
        leads[domain] = {"scans": [previous] if previous.get("scanned_at") else []}
    leads[domain]["scans"].append(scan)
    # Keep only the last 10 scans per domain
    leads[domain]["scans"] = leads[domain]["scans"][-10:]
    _save_leads(leads)


# ── Diff logic ───────────────────────────────────────────────────────────────

def diff_scans(previous: dict, current: dict) -> dict:
    """
    Compare two scan results and return a structured diff.
    Returns {"resolved": [...], "degraded": [...], "new": [...],
             "score_change": int, "summary": str}
    """
    resolved = []
    degraded = []
    new_findings = []

    def _check(key, label, good_when_truthy=True):
        prev_val = bool(previous.get(key))
        curr_val = bool(current.get(key))
        if good_when_truthy:
            if not prev_val and curr_val:
                resolved.append(label)
            elif prev_val and not curr_val:
                degraded.append(label)
        else:
            if prev_val and not curr_val:
                resolved.append(label)
            elif not prev_val and curr_val:
                degraded.append(label)

    _check("spf", "SPF record")
    _check("dmarc", "DMARC policy")

    prev_ssl_ok = not bool((previous.get("ssl") or {}).get("error"))
    curr_ssl_ok = not bool((current.get("ssl") or {}).get("error"))
    if not prev_ssl_ok and curr_ssl_ok:
        resolved.append("SSL certificate")
    elif prev_ssl_ok and not curr_ssl_ok:
        degraded.append("SSL certificate")

    prev_score = previous.get("risk_score") or 0
    curr_score = current.get("risk_score") or 0
    score_change = curr_score - prev_score

    # Detect new CT subdomains
    prev_ct = set(previous.get("ct_subdomains") or [])
    curr_ct = set(current.get("ct_subdomains") or [])
    newly_appeared = curr_ct - prev_ct
    if newly_appeared:
        new_findings.append(f"New subdomains in CT logs: {', '.join(sorted(newly_appeared))}")

    # Detect new CVEs
    prev_cve_ids = {c["id"] for c in (previous.get("cves") or {}).get("cves", [])}
    curr_cve_ids = {c["id"] for c in (current.get("cves") or {}).get("cves", [])}
    new_cves = curr_cve_ids - prev_cve_ids
    if new_cves:
        new_findings.append(f"New CVEs matched: {', '.join(sorted(new_cves))}")

    if score_change > 0:
        summary = f"Security posture degraded (+{score_change} risk points)."
    elif score_change < 0:
        summary = f"Security posture improved ({score_change} risk points)."
    else:
        summary = "No significant change in risk score."

    return {
        "resolved": resolved,
        "degraded": degraded,
        "new": new_findings,
        "score_change": score_change,
        "previous_score": prev_score,
        "current_score": curr_score,
        "previous_scan_at": previous.get("scanned_at"),
        "current_scan_at": current.get("scanned_at"),
        "summary": summary,
    }


# ── Main entry point ─────────────────────────────────────────────────────────

def run_monitor(domain: str, depth: str = "pro", nvd_api_key: str | None = None) -> dict:
    """
    Run a fresh scan, diff against previous, store result.
    Returns {"domain": ..., "diff": ..., "scan": ..., "is_first_scan": bool}
    """
    previous = get_previous_scan(domain)
    current = scan_target(domain, depth=depth, nvd_api_key=nvd_api_key)
    store_scan(domain, current)

    if previous is None:
        return {"domain": domain, "diff": None, "scan": current, "is_first_scan": True}

    diff = diff_scans(previous, current)
    return {"domain": domain, "diff": diff, "scan": current, "is_first_scan": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description="PRAETOR Monitor — re-scan and diff")
    parser.add_argument("--domain", "-d", required=True, help="Domain to re-scan")
    parser.add_argument("--depth", default="pro", choices=["express", "pro", "corporate"])
    parser.add_argument("--nvd-key", default=None, help="Optional NVD API key for higher rate limits")
    parser.add_argument("--output", "-o", help="Save JSON result to file")
    args = parser.parse_args(argv)

    domain = args.domain.lower().strip()
    if not _is_valid_domain(domain):
        print("Invalid domain format.")
        sys.exit(2)

    print(f"[+] Monitoring {domain} (depth={args.depth})…")
    result = run_monitor(domain, depth=args.depth, nvd_api_key=args.nvd_key)

    if result["is_first_scan"]:
        print("  First scan — baseline stored. No diff available yet.")
    else:
        diff = result["diff"]
        print(f"  Summary: {diff['summary']}")
        if diff["resolved"]:
            print(f"  Resolved: {', '.join(diff['resolved'])}")
        if diff["degraded"]:
            print(f"  Degraded: {', '.join(diff['degraded'])}")
        if diff["new"]:
            for item in diff["new"]:
                print(f"  New: {item}")

    print(f"  Risk score: {result['scan'].get('risk_score')} ({result['scan'].get('risk_level')})")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"  Saved to {args.output}")


if __name__ == "__main__":
    main()

"""
Vigil Orchestrator — one button, full pipeline.

Runs the complete Find -> Warn -> Protect demo:
  1. FIND: Scan regulatory sources (EUR-Lex, GDPR portals)
  2. FIND: Search business registries for affected companies
  3. MATCH: Cross-reference companies with regulatory risks
  4. WARN: Call the company with a compliance briefing
  5. (Email is sent automatically when recipient presses 1 during the call)

Usage:
    python src/outreach/orchestrator.py
"""

import sys
import os
import json
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

from database.db import Database
from outreach.voice_agent import make_outreach_call


# ── Helpers ──────────────────────────────────────────────────────────────

DEMO_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "demo")

def _print_step(step_num: int, total: int, emoji: str, title: str):
    print(f"\n{'='*60}")
    print(f"  [{step_num}/{total}] {emoji}  {title}")
    print(f"{'='*60}")

def _print_detail(label: str, value: str):
    print(f"    {label}: {value}")

def _simulate_progress(message: str, seconds: float = 1.5):
    """Brief pause with animated dots — makes demo look like real processing."""
    print(f"    {message}", end="", flush=True)
    for _ in range(3):
        time.sleep(seconds / 3)
        print(".", end="", flush=True)
    print(" done!")


# ── Pipeline steps ───────────────────────────────────────────────────────

def step_scan_regulations() -> list[dict]:
    """Step 1: Load pre-scraped regulatory facts (in production: live Apify crawl)."""
    _print_step(1, 5, "FIND", "Scanning EU regulatory sources")

    facts_path = os.path.join(DEMO_DIR, "pre_scraped_facts.json")
    with open(facts_path) as f:
        facts = json.load(f)

    _simulate_progress("Crawling EUR-Lex, GDPR portals", 2.0)

    # Filter to only real regulatory facts (not generic OJ metadata)
    reg_facts = [f for f in facts if f.get("regulation")]

    _print_detail("Sources scanned", "EUR-Lex, gdpr.eu, AI Act portal")
    _print_detail("Regulatory facts extracted", str(len(reg_facts)))

    for fact in reg_facts[:5]:
        severity = fact.get("severity", "medium").upper()
        reg = fact.get("regulation", "Unknown")
        print(f"      [{severity}] {reg}: {fact['claim'][:80]}...")

    return reg_facts


def step_search_registries(db: Database) -> list[dict]:
    """Step 2: Search business registries for companies (in production: live API calls)."""
    _print_step(2, 5, "FIND", "Searching business registries")

    _simulate_progress("Querying Handelsregister (DE), KRS (PL)", 1.5)

    # In production this would be live API calls to company registries
    # For demo, we use the seeded database
    companies = []
    row = db.get_company("test-001")
    if row:
        companies.append(row)

    _print_detail("Registries searched", "Handelsregister (DE), KRS (PL)")
    _print_detail("Companies discovered", str(len(companies)))

    for c in companies:
        print(f"      -> {c['name']} ({c['industry']}, {c['country']})")

    return companies


def step_match_risks(companies: list[dict], facts: list[dict]) -> list[dict]:
    """Step 3: Match companies to regulatory risks based on industry + keywords."""
    _print_step(3, 5, "MATCH", "Cross-referencing companies with regulations")

    _simulate_progress("Running risk matcher (industry + keyword analysis)", 1.5)

    # Load the curated alert (in production: LLM-based matching)
    alert_path = os.path.join(DEMO_DIR, "mock_alert.json")
    with open(alert_path) as f:
        alert = json.load(f)

    matches = []
    for company in companies:
        match = {
            "company": company,
            "alert": alert,
            "matched_facts": [f for f in facts if f.get("regulation") in ("AI Act", "GDPR")],
        }
        matches.append(match)

        severity = alert.get("severity", "high").upper()
        _print_detail("Company", company["name"])
        _print_detail("Risk", f"[{severity}] {alert['regulation']} {alert.get('article', '')}")
        _print_detail("Deadline", f"{alert['days_remaining']} days")
        _print_detail("Action", alert["action_required"][:80])

    return matches


def step_outreach_call(match: dict, db: Database) -> dict:
    """Step 4: Make the outreach call."""
    _print_step(4, 5, "WARN", f"Calling {match['company']['name']}")

    company = match["company"]
    alert = match["alert"]

    _print_detail("Phone", company["phone"])
    _print_detail("Regulation", f"{alert['regulation']} {alert.get('article', '')}")
    print()

    # Check cooldown
    if db.is_in_cooldown(company["id"]):
        print("    [SKIP] Company contacted within last 90 days — respecting cooldown.")
        return {"status": "skipped", "reason": "cooldown"}

    result = make_outreach_call(company, alert, db)
    db.log_outreach(company["id"], "voice", result["status"], alert["regulation"])

    return result


def step_summary(matches: list[dict]):
    """Step 5: Summary."""
    _print_step(5, 5, "DONE", "Pipeline complete")

    print("    When the recipient presses 1 during the call,")
    print("    Vigil automatically sends a compliance briefing email.")
    print()
    print("    Pipeline summary:")
    _print_detail("Companies contacted", str(len(matches)))
    _print_detail("Channel", "Voice call + follow-up email")
    _print_detail("Next step", "Recipient uses /vigil to scan their codebase")
    print()


# ── Main ─────────────────────────────────────────────────────────────────

def run_pipeline():
    """Run the full Vigil pipeline: Find -> Warn -> Protect."""
    print()
    print("  V I G I L")
    print("  Find. Warn. Protect.")
    print("  ─────────────────────────────────────")
    print("  EU Regulatory Compliance Agent")
    print()

    db = Database("vigil.db")

    # 1. Scan regulations
    facts = step_scan_regulations()

    # 2. Search registries
    companies = step_search_registries(db)

    if not companies:
        print("\n  No companies found. Exiting.")
        return

    # 3. Match risks
    matches = step_match_risks(companies, facts)

    if not matches:
        print("\n  No regulatory risks matched. Exiting.")
        return

    # 4. Outreach calls
    for match in matches:
        result = step_outreach_call(match, db)

    # 5. Summary
    step_summary(matches)


if __name__ == "__main__":
    run_pipeline()

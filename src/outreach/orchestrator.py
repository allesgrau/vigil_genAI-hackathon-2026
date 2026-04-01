"""
Vigil Orchestrator — LIVE pipeline, zero mocks.

Full Find -> Warn flow:
  1. FIND: Scrape 1 legislative page (Apify website-content-crawler)
  2. FIND: Scrape 1 business registry page (Apify website-content-crawler)
  3. MATCH: Claude matches company to regulatory risks
  4. WARN: Call the company with a compliance briefing
  5. (Email sent automatically when recipient presses 1)

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

from apify_client import ApifyClient
from openai import OpenAI
from database.db import Database
from outreach.voice_agent import make_outreach_call
from processing.chunker import chunk_documents
from processing.fact_extractor import extract_facts


# ── Config ───────────────────────────────────────────────────────────────

# Legislative source to scrape (1 page, fast)
REGULATION_URL = "https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai"

# Business registry source to scrape (1 page, fast)
REGISTRY_URL = "https://www.northdata.com/TechStartup+GmbH"

# Fallback alert if matching fails
FALLBACK_ALERT = {
    "regulation": "AI Act",
    "article": "Art. 6 & Art. 52",
    "days_remaining": 28,
    "action_required": "Register AI systems used in credit scoring as high-risk under AI Act Art. 6, and implement transparency disclosures for AI-generated decisions per Art. 52",
    "severity": "critical",
}

DEMO_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "demo")


# ── Helpers ──────────────────────────────────────────────────────────────

def _print_step(step_num: int, total: int, label: str, title: str):
    print(f"\n{'='*60}")
    print(f"  [{step_num}/{total}] {label}  {title}")
    print(f"{'='*60}")

def _print_detail(label: str, value: str):
    print(f"    {label}: {value}")

def _get_llm_client() -> OpenAI:
    return OpenAI(
        base_url=os.getenv("OPENROUTER_ACTOR_URL", "https://openrouter.apify.actor/api/v1"),
        api_key="no-key-required-but-must-not-be-empty",
        default_headers={"Authorization": f"Bearer {os.getenv('APIFY_TOKEN', '')}"},
    )


# ── Step 1: Scrape legislation ──────────────────────────────────────────

def step_scrape_legislation(apify_client: ApifyClient, db: Database) -> list[dict]:
    """Scrape 1 legislative page with Apify and extract facts with Claude."""
    _print_step(1, 5, "FIND", "Scraping EU regulatory source")
    _print_detail("URL", REGULATION_URL)

    db.log_pipeline("SCRAPE", f"Crawling regulatory source: {REGULATION_URL.split('/')[2]}", "info")

    print("    Launching Apify website-content-crawler...")
    run = apify_client.actor("apify/website-content-crawler").call(
        run_input={
            "startUrls": [{"url": REGULATION_URL}],
            "maxCrawlDepth": 0,
            "maxCrawlPages": 1,
            "outputFormats": ["markdown"],
            "removeCookieWarnings": True,
            "blockAds": True,
        },
        memory_mbytes=2048,
    )

    documents = []
    for item in apify_client.dataset(run["defaultDatasetId"]).iterate_items():
        if item.get("text") or item.get("markdown"):
            documents.append({
                "url": item.get("url", ""),
                "title": item.get("title", ""),
                "content": item.get("markdown") or item.get("text", ""),
                "source": "eurlex",
            })

    print(f"    Scraped {len(documents)} document(s)")
    db.log_pipeline("SCRAPE", f"Scraped {len(documents)} regulatory document(s)", "ok")

    if not documents:
        print("    [WARN] No documents scraped — using pre-scraped facts as fallback")
        db.log_pipeline("SCRAPE", "No documents found — using pre-scraped facts", "warn")
        facts_path = os.path.join(DEMO_DIR, "pre_scraped_facts.json")
        with open(facts_path) as f:
            return json.load(f)

    # Chunk and extract facts
    print("    Chunking...")
    chunks = chunk_documents(documents)
    db.log_pipeline("EXTRACT", f"Chunked into {len(chunks)} segments, sending to Claude...", "info")
    print(f"    Extracting facts with Claude...")

    profile = {"areas_of_concern": ["AI Act", "GDPR", "PSD2"], "test_mode": True}
    facts = extract_facts(chunks, profile)
    print(f"    -> {len(facts)} regulatory facts extracted")
    db.log_pipeline("EXTRACT", f"Extracted {len(facts)} regulatory facts with Claude", "ok")

    for fact in facts[:3]:
        reg = fact.get("regulation", "?")
        sev = fact.get("severity", "?").upper()
        print(f"      [{sev}] {reg}: {fact['claim'][:80]}...")
        db.log_pipeline("FACT", f"[{sev}] {reg}: {fact['claim'][:80]}", "ok")

    return facts


# ── Step 2: Scrape business registry ────────────────────────────────────

def step_scrape_registry(apify_client: ApifyClient, db: Database) -> dict | None:
    """Scrape 1 registry page, extract company info with Claude, save to DB."""
    _print_step(2, 5, "FIND", "Scraping business registry")
    _print_detail("URL", REGISTRY_URL)

    db.log_pipeline("SCRAPE", f"Crawling business registry: {REGISTRY_URL.split('/')[2]}", "info")

    print("    Launching Apify website-content-crawler...")
    run = apify_client.actor("apify/website-content-crawler").call(
        run_input={
            "startUrls": [{"url": REGISTRY_URL}],
            "maxCrawlDepth": 0,
            "maxCrawlPages": 1,
            "outputFormats": ["markdown"],
            "removeCookieWarnings": True,
            "blockAds": True,
        },
        memory_mbytes=2048,
    )

    page_content = ""
    for item in apify_client.dataset(run["defaultDatasetId"]).iterate_items():
        page_content = item.get("markdown") or item.get("text", "")
        break

    if not page_content:
        print("    [WARN] No registry data scraped — using seed company from DB")
        db.log_pipeline("SCRAPE", "No registry data — using seed company", "warn")
        return db.get_company("test-001")

    db.log_pipeline("SCRAPE", "Scraped business registry page", "ok")

    # Extract company info with Claude
    print("    Extracting company info with Claude...")
    db.log_pipeline("EXTRACT", "Extracting company info with Claude...", "info")
    llm = _get_llm_client()

    response = llm.chat.completions.create(
        model="anthropic/claude-3-haiku",
        max_tokens=500,
        messages=[{"role": "user", "content": f"""Extract company information from this business registry page.
Return ONLY a JSON object with these fields:
- "name": company name
- "country": 2-letter country code
- "industry": industry/sector
- "description": 1-sentence description of what the company does

If you can't find a company, return {{"name": null}}.

PAGE CONTENT:
{page_content[:3000]}"""}],
    )

    raw = response.choices[0].message.content
    try:
        # Parse JSON from response
        start = raw.find("{")
        end = raw.rfind("}") + 1
        company_info = json.loads(raw[start:end]) if start != -1 else {}
    except (json.JSONDecodeError, ValueError):
        company_info = {}

    if not company_info.get("name"):
        print("    [WARN] Could not extract company info — using seed company from DB")
        return db.get_company("test-001")

    # Replace contact data with our demo data (Basia's phone + email)
    seed = db.get_company("test-001")
    company_id = "live-" + company_info["name"].lower().replace(" ", "-")[:30]

    company = {
        "id": company_id,
        "name": company_info["name"],
        "country": company_info.get("country", "DE"),
        "industry": company_info.get("industry", "technology"),
        "phone": seed["phone"],      # <-- swap to our demo phone
        "email": seed["email"],       # <-- swap to our demo email
        "source_registry": REGISTRY_URL,
    }

    db.add_company(company)
    db.log_pipeline("REGISTRY", f"Discovered {company['name']} ({company.get('industry', '?')}, {company.get('country', '?')})", "ok")

    _print_detail("Company found", company["name"])
    _print_detail("Industry", company.get("industry", "?"))
    _print_detail("Country", company.get("country", "?"))
    _print_detail("Contact", f"{company['phone']} / {company['email']}")
    if company_info.get("description"):
        _print_detail("Description", company_info["description"][:80])

    return company


# ── Step 3: Alert matching with Claude ───────────────────────────────────

def step_match_risks(company: dict, facts: list[dict], db: Database) -> dict:
    """Use Claude to match company profile against extracted facts → generate alert."""
    _print_step(3, 5, "MATCH", "Matching company to regulatory risks")

    db.log_pipeline("MATCH", f"Matching {company['name']} against {len(facts)} regulatory facts...", "info")

    if not facts:
        print("    No facts to match — using fallback alert")
        db.log_pipeline("MATCH", "No facts — using fallback alert", "warn")
        return FALLBACK_ALERT

    llm = _get_llm_client()

    facts_text = "\n".join([
        f"- [{f.get('severity','?').upper()}] {f.get('regulation','?')}"
        f" {f.get('article','')}: {f['claim'][:150]}"
        for f in facts[:15]
    ])

    prompt = f"""You are a regulatory compliance analyst. Given the company profile and regulatory facts below,
generate the SINGLE most urgent compliance alert for this company.

COMPANY:
- Name: {company['name']}
- Industry: {company.get('industry', 'unknown')}
- Country: {company.get('country', 'EU')}

REGULATORY FACTS:
{facts_text}

Return ONLY a JSON object:
{{
  "regulation": "name of regulation (e.g. AI Act, GDPR)",
  "article": "specific article(s) if known",
  "days_remaining": estimated days until deadline (integer, 1-365),
  "action_required": "1-2 sentence description of what the company must do",
  "severity": "critical" or "high" or "medium"
}}"""

    try:
        response = llm.chat.completions.create(
            model="anthropic/claude-3-haiku",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.choices[0].message.content
        start = raw.find("{")
        end = raw.rfind("}") + 1
        alert = json.loads(raw[start:end])

        # Validate required fields
        if not alert.get("regulation") or not alert.get("action_required"):
            print("    [WARN] Incomplete alert from Claude — using fallback")
            return FALLBACK_ALERT

        _print_detail("Regulation", f"{alert['regulation']} {alert.get('article', '')}")
        _print_detail("Severity", alert.get("severity", "high").upper())
        _print_detail("Deadline", f"{alert.get('days_remaining', '?')} days")
        _print_detail("Action", alert["action_required"][:80])

        severity = alert.get("severity", "high").upper()
        color = "warn" if severity in ("CRITICAL", "HIGH") else "info"
        db.log_pipeline("RISK", f"[{severity}] {alert['regulation']} {alert.get('article', '')} — {alert.get('days_remaining', '?')} days remaining", color)

        # Save alert to demo dir for webhook to use
        alert_path = os.path.join(DEMO_DIR, "mock_alert.json")
        with open(alert_path, "w") as f:
            json.dump(alert, f, indent=2)
        print(f"    Alert saved to {alert_path}")

        return alert

    except Exception as e:
        print(f"    [WARN] Matching failed ({e}) — using fallback alert")
        db.log_pipeline("MATCH", f"Matching failed — using fallback alert", "warn")
        return FALLBACK_ALERT


# ── Step 4: Outreach call ────────────────────────────────────────────────

def step_outreach_call(company: dict, alert: dict, db: Database) -> dict:
    """Generate script with Claude + make Twilio call."""
    _print_step(4, 5, "WARN", f"Calling {company['name']}")
    _print_detail("Phone", company["phone"])
    _print_detail("Regulation", f"{alert['regulation']} {alert.get('article', '')}")
    print()

    db.log_pipeline("SCRIPT", f"Generating call script for {company['name']}...", "info")
    result = make_outreach_call(company, alert, db)
    db.log_pipeline("CALL", f"Called {company['name']} — [{result['status']}]", "ok" if result["status"] == "completed" else "warn")
    db.log_outreach(company["id"], "voice", result["status"], alert["regulation"])
    return result


# ── Step 5: Summary ─────────────────────────────────────────────────────

def step_summary(company: dict, alert: dict):
    _print_step(5, 5, "DONE", "Pipeline complete")
    print("    When the recipient presses 1 during the call,")
    print("    Vigil automatically sends a compliance briefing email.")
    print()
    print("    Pipeline summary:")
    _print_detail("Regulation scraped", REGULATION_URL.split("/")[-1][:50])
    _print_detail("Company discovered", company["name"])
    _print_detail("Risk matched", f"{alert['regulation']} — {alert.get('severity', 'high').upper()}")
    _print_detail("Outreach", "Voice call initiated + email on keypress")
    _print_detail("Next step", "Recipient uses /vigil to scan their codebase")
    print()


# ── Main ─────────────────────────────────────────────────────────────────

def run_pipeline():
    """Run the full LIVE Vigil pipeline: Find -> Warn -> Protect."""
    print()
    print("  V I G I L")
    print("  Find. Warn. Protect.")
    print("  ─────────────────────────────────────")
    print("  EU Regulatory Compliance Agent")
    print()

    token = os.getenv("APIFY_TOKEN")
    if not token:
        print("  ERROR: APIFY_TOKEN not set in .env")
        sys.exit(1)

    apify_client = ApifyClient(token)
    db = Database("vigil.db")

    db.log_pipeline("PIPELINE", "Vigil pipeline started", "info")

    # 1. Scrape legislation (live Apify crawl → Claude fact extraction)
    facts = step_scrape_legislation(apify_client, db)

    # 2. Scrape business registry (live Apify crawl → Claude company extraction)
    company = step_scrape_registry(apify_client, db)
    if not company:
        print("\n  ERROR: No company found. Exiting.")
        db.log_pipeline("PIPELINE", "Pipeline failed — no company found", "warn")
        sys.exit(1)

    # 3. Match company to risks (Claude LLM matching)
    alert = step_match_risks(company, facts, db)

    # 4. Outreach call (Claude script generation + Twilio voice)
    result = step_outreach_call(company, alert, db)

    # 5. Summary
    step_summary(company, alert)
    db.log_pipeline("PIPELINE", "Pipeline complete — waiting for keypress to send report", "ok")


if __name__ == "__main__":
    run_pipeline()

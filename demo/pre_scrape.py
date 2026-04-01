import asyncio
import json
import os
import sys

# Add src/ to path so imports work like they do inside Apify Actor
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dotenv import load_dotenv
load_dotenv()

from apify_client import ApifyClient
from scrapers.eurlex_scraper import scrape_eurlex
from scrapers.gdpr_scraper import scrape_gdpr
from scrapers.national_scraper import scrape_national
from processing.chunker import chunk_documents
from processing.fact_extractor import extract_facts
from processing.embedder import embed_facts
from processing.relevance_filter import filter_relevant
from rag.retriever import retrieve
from digest.digest_generator import generate_digest
from digest.alert_engine import generate_alerts
from digest.formatter import format_output


DEMO_DIR = os.path.dirname(__file__)

# Company profile for demo — fintech in Germany
COMPANY_PROFILE = {
    "company_name": "TechStartup GmbH",
    "industry": "fintech",
    "country": "DE",
    "size": "startup",
    "areas_of_concern": ["GDPR", "AI Act", "PSD2"],
    "test_mode": True,  # limits scraping for speed
}


async def main():
    token = os.getenv("APIFY_TOKEN")
    if not token:
        print("ERROR: APIFY_TOKEN not set in .env")
        sys.exit(1)

    client = ApifyClient(token=token)
    profile = COMPANY_PROFILE

    print(f"\n{'='*60}")
    print(f"  VIGIL PRE-SCRAPE — {profile['company_name']}")
    print(f"  Industry: {profile['industry']} | Country: {profile['country']}")
    print(f"  Areas: {', '.join(profile['areas_of_concern'])}")
    print(f"{'='*60}\n")

    # Step 1: Scrape
    print("[1/7] Scraping regulatory sources...")
    eurlex_docs, gdpr_docs, national_docs = await asyncio.gather(
        scrape_eurlex(client, profile, test_mode=True),
        scrape_gdpr(client, profile, test_mode=True),
        scrape_national(client, profile, test_mode=True),
    )
    raw_documents = eurlex_docs + gdpr_docs + national_docs
    print(f"  -> {len(raw_documents)} documents scraped\n")

    # Step 2: Chunk
    print("[2/7] Chunking documents...")
    chunks = chunk_documents(raw_documents)
    print(f"  -> {len(chunks)} chunks\n")

    # Step 3: Extract facts
    print("[3/7] Extracting facts with Claude...")
    facts = extract_facts(chunks, profile)
    print(f"  -> {len(facts)} facts extracted\n")

    # Save raw facts
    facts_path = os.path.join(DEMO_DIR, "pre_scraped_facts.json")
    with open(facts_path, "w", encoding="utf-8") as f:
        json.dump(facts, f, indent=2, ensure_ascii=False)
    print(f"  -> Saved to {facts_path}\n")

    # Step 4: Embed
    print("[4/7] Embedding facts...")
    embedded_facts = embed_facts(facts)

    # Step 5: Filter
    print("[5/7] Filtering relevant facts...")
    relevant = filter_relevant(embedded_facts, profile)
    print(f"  -> {len(relevant)} relevant facts\n")

    # Step 6: Retrieve
    print("[6/7] Retrieving top facts...")
    retrieved = retrieve(relevant, profile)
    print(f"  -> {len(retrieved)} retrieved\n")

    # Step 7: Generate digest + alerts
    print("[7/7] Generating digest and alerts...")
    digest = generate_digest(retrieved, profile, client)
    alerts = generate_alerts(retrieved, profile)
    output = format_output(digest, alerts, profile)

    # Save full output
    output_path = os.path.join(DEMO_DIR, "pre_scraped_output.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"  -> Full output saved to {output_path}\n")

    # Create mock_alert.json from the best alert (or first fact if no alerts)
    if alerts:
        best_alert = alerts[0]  # already sorted by severity
        mock_alert = {
            "regulation": best_alert.get("regulation", best_alert.get("title", "AI Act")),
            "article": best_alert.get("article", ""),
            "days_remaining": best_alert.get("days_remaining", 28),
            "action_required": best_alert.get("action_required", best_alert.get("title", "")),
            "severity": best_alert.get("severity", "critical"),
        }
    elif facts:
        best_fact = facts[0]
        mock_alert = {
            "regulation": best_fact.get("regulation", "AI Act"),
            "article": best_fact.get("article", "Art. 52"),
            "days_remaining": 28,
            "action_required": best_fact.get("action_required", best_fact.get("claim", "")),
            "severity": best_fact.get("severity", "critical"),
        }
    else:
        # Hardcoded fallback
        mock_alert = {
            "regulation": "AI Act",
            "article": "Art. 52",
            "days_remaining": 28,
            "action_required": "Register AI systems used in credit scoring and implement transparency disclosures",
            "severity": "critical",
        }

    alert_path = os.path.join(DEMO_DIR, "mock_alert.json")
    with open(alert_path, "w", encoding="utf-8") as f:
        json.dump(mock_alert, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*60}")
    print(f"  DONE!")
    print(f"  Facts:      {facts_path}")
    print(f"  Mock alert: {alert_path}")
    print(f"  Full output:{output_path}")
    print(f"{'='*60}\n")

    # Preview the mock alert
    print("Mock alert for demo:")
    print(json.dumps(mock_alert, indent=2))


if __name__ == "__main__":
    asyncio.run(main())

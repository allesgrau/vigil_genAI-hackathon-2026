import asyncio
from apify_client import ApifyClient
from apify import Actor
from dotenv import load_dotenv
import os

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

load_dotenv()


async def main():

    async with Actor:

        company_profile = await Actor.get_input() or {
            "company_name": "TechStartup GmbH",
            "industry": "fintech",
            "country": "DE",
            "size": "startup",
            "areas_of_concern": ["GDPR", "AI Act", "PSD2"],
            "test_mode": True
        }

        client = ApifyClient(token=os.getenv("APIFY_TOKEN"))

        print(f"Vigil starting for: {company_profile['company_name']}")

        # Step 1: Scraping
        print("Scraping regulatory sources...")
        test_mode = company_profile.get("test_mode", False)
        eurlex_docs = await scrape_eurlex(client, company_profile, test_mode=test_mode)
        gdpr_docs = await scrape_gdpr(client, company_profile, test_mode=test_mode)
        national_docs = await scrape_national(client, company_profile, test_mode=test_mode)

        raw_documents = eurlex_docs + gdpr_docs + national_docs
        print(f"Total documents scraped: {len(raw_documents)}")

        # Step 2: Chunking (intermediate step to break down large documents into smaller pieces)
        print("Chunking documents...")
        chunks = chunk_documents(raw_documents)

        # Step 3: Extract facts from chunks
        print("Extracting facts...")
        facts = extract_facts(chunks, company_profile)

        # Step 4: Embed facts
        print("Embedding facts...")
        embedded_facts = embed_facts(facts)

        # Step 5: Filter relevant facts
        print("Filtering relevant facts...")
        relevant = filter_relevant(embedded_facts, company_profile)

        # Step 6: Retrieval
        print("Retrieving relevant facts...")
        retrieved = retrieve(relevant, company_profile)

        # Step 7: Generate digest and alerts
        print("Generating digest and alerts...")
        digest = generate_digest(retrieved, company_profile, client)
        alerts = generate_alerts(retrieved, company_profile)

        # Step 8: Format output
        output = format_output(digest, alerts, company_profile)

        # Save output to Apify dataset
        await Actor.push_data(output)

        print("\nVIGIL DIGEST READY\n")
        print(output)


if __name__ == "__main__":

    asyncio.run(main())
from apify_client import ApifyClient


async def scrape_eurlex(client: ApifyClient, company_profile: dict) -> list[dict]:
    """
    Scrape EUR-Lex for recent regulatory updates using Apify's website-content-crawler Actor.
    """
    
    areas = company_profile.get("areas_of_concern", [])
    
    # Build list of EUR-Lex URLs to scrape based on the company's areas of concern
    start_urls = _build_urls(areas)
    
    print(f"Scraping {len(start_urls)} EUR-Lex sources for: {areas}")
    
    run = client.actor("apify/website-content-crawler").call(
        run_input={
            "startUrls": [{"url": url} for url in start_urls],
            "maxCrawlDepth": 1,
            "maxCrawlPages": 30,
            "outputFormats": ["markdown"],
            "removeCookieWarnings": True,
            "blockAds": True,
        }
    )
    
    # Get the scraped data from the Actor's dataset
    documents = []
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        if item.get("text") or item.get("markdown"):
            documents.append({
                "url": item.get("url", ""),
                "title": item.get("title", ""),
                "content": item.get("markdown") or item.get("text", ""),
                "crawled_at": item.get("crawl", {}).get("loadedAt", ""),
                "source": "eurlex"
            })
    
    print(f"Scraped {len(documents)} documents from EUR-Lex")
    return documents


def _build_urls(areas: list[str]) -> list[str]:
    """
    Map areas of concern to specific EUR-Lex URLs. Always include the direct access page for the latest acts.
    """
    
    area_to_urls = {
        "GDPR": [
            "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32016R0679",
            "https://eur-lex.europa.eu/search.html?query=GDPR&DB_TYPE_OF_ACT=regulation"
        ],
        "AI Act": [
            "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32024R1689",
            "https://eur-lex.europa.eu/search.html?query=artificial+intelligence+act"
        ],
        "PSD2": [
            "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32015L2366",
        ],
        "AML": [
            "https://eur-lex.europa.eu/search.html?query=anti+money+laundering"
        ],
        "NIS2": [
            "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32022L2555"
        ],
        "DORA": [
            "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32022R2554"
        ],
    }
    
    urls = [
        # Always scrape the page for the latest acts
        "https://eur-lex.europa.eu/oj/direct-access.html",
    ]
    
    for area in areas:
        if area in area_to_urls:
            urls.extend(area_to_urls[area])
    
    return list(set(urls))
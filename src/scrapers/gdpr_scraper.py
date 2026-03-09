from apify_client import ApifyClient


async def scrape_gdpr(client: ApifyClient, company_profile: dict) -> list[dict]:
    """
    Scrape GDPR-specific sources:
    - gdpr.eu — practical guides and checklists
    - edpb.europa.eu — European Data Protection Board (official opinions)
    - iapp.org — industry news about privacy
    """

    country = company_profile.get("country", "").upper()

    start_urls = [
        "https://edpb.europa.eu/news/news_en",
        "https://edpb.europa.eu/our-work-tools/our-documents/guidelines_en",
        "https://gdpr.eu/what-is-gdpr/",
        "https://gdpr.eu/checklist/",
    ]

    # Add national DPA website if country is known and supported
    national_dpa = _get_national_dpa(country)
    if national_dpa:
        start_urls.append(national_dpa)

    print(f"Scraping GDPR sources ({len(start_urls)} URLs)...")

    run = client.actor("apify/website-content-crawler").call(
        run_input={
            "startUrls": [{"url": url} for url in start_urls],
            "maxCrawlDepth": 1,
            "maxCrawlPages": 20,
            "outputFormats": ["markdown"],
            "removeCookieWarnings": True,
            "blockAds": True,
        }
    )

    documents = []
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        if item.get("text") or item.get("markdown"):
            documents.append({
                "url": item.get("url", ""),
                "title": item.get("title", ""),
                "content": item.get("markdown") or item.get("text", ""),
                "crawled_at": item.get("crawl", {}).get("loadedAt", ""),
                "source": "gdpr"
            })

    print(f"craped {len(documents)} GDPR documents")
    return documents


def _get_national_dpa(country: str) -> str | None:
    """
    Returns the URL of the national Data Protection Authority (DPA) for a given country.
    """

    dpa_urls = {
        "DE": "https://www.bfdi.bund.de/EN/Home/home_node.html",
        "PL": "https://uodo.gov.pl/en",
        "FR": "https://www.cnil.fr/en/home",
        "NL": "https://www.autoriteitpersoonsgegevens.nl/en",
        "CH": "https://www.edoeb.admin.ch/edoeb/en/home.html",
        "IT": "https://www.garanteprivacy.it/web/guest/home/docweb",
        "ES": "https://www.aepd.es/en",
        "SE": "https://www.imy.se/en/",
        "AT": "https://www.dsb.gv.at/",
        "BE": "https://www.dataprotectionauthority.be/",
    }

    return dpa_urls.get(country)
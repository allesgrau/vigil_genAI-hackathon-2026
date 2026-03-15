from apify_client import ApifyClient


async def scrape_national(client: ApifyClient, company_profile: dict, test_mode: bool = True) -> list[dict]:

    country = company_profile.get("country", "").upper()
    industry = company_profile.get("industry", "").lower()
    start_urls = _get_national_urls(country, industry)

    if not start_urls:
        print(f"⚠️ No national sources configured for country: {country}")
        return []

    if test_mode:
        start_urls = start_urls[:1]
        max_pages = 3
        max_depth = 0
    else:
        max_pages = 15
        max_depth = 1

    print(f"📡 Scraping national sources for {country} {'[TEST MODE]' if test_mode else ''} ({len(start_urls)} URLs)...")

    run = client.actor("apify/website-content-crawler").call(
        run_input={
            "startUrls": [{"url": url} for url in start_urls],
            "maxCrawlDepth": max_depth,
            "maxCrawlPages": max_pages,
            "outputFormats": ["markdown"],
            "removeCookieWarnings": True,
            "blockAds": True,
        },
        memory_mbytes=2048
    )

    documents = []
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        if item.get("text") or item.get("markdown"):
            documents.append({
                "url": item.get("url", ""),
                "title": item.get("title", ""),
                "content": item.get("markdown") or item.get("text", ""),
                "crawled_at": item.get("crawl", {}).get("loadedAt", ""),
                "source": f"national_{country.lower()}"
            })

    print(f"✅ Scraped {len(documents)} national documents for {country}")
    return documents


def _get_national_urls(country: str, industry: str) -> list[str]:

    base_urls = {
        "DE": [
            "https://www.gesetze-im-internet.de/aktuell.html",
            "https://www.bundesanzeiger.de/pub/en/start",
            "https://www.bsi.bund.de/DE/Themen/Unternehmen-und-Organisationen/Informationen-und-Empfehlungen/Empfehlungen-nach-Angriffszielen/Industriesteuerungen/KRITIS/kritis_node.html",
        ],
        "PL": [
            "https://dziennikustaw.gov.pl/najnowsze",
            "https://legislacja.gov.pl/projekty/lista",
            "https://uodo.gov.pl/pl/138"
        ],
        "FR": [
            "https://www.legifrance.gouv.fr/liste/jo",
            "https://www.service-public.fr/actualites",
            "https://www.cnil.fr/fr/news",
            "https://www.amf-france.org/fr/actualites-publications/actualites"
        ],
        "CH": [
            "https://www.admin.ch/gov/en/start/documentation/media-releases.html",
            "https://www.seco.admin.ch/seco/en/home/Arbeit/Arbeitsbedingungen.html",
            "https://www.edoeb.admin.ch/edoeb/de/home/aktuell.html"
        ],
        "NL": [
            "https://wetten.overheid.nl/zoeken",
            "https://www.autoriteitpersoonsgegevens.nl/en/news",
            "https://www.dnb.nl/en/news/"
        ],
        "IT": [
            "https://www.gazzettaufficiale.it/home",
            "https://www.garanteprivacy.it/home/docweb/-/docweb-display/docweb/9691942",
            "https://www.bancaditalia.it/media/notizie/index.html"
        ],
        "ES": [
            "https://www.aepd.es/en/press-and-communications/news",
            "https://www.boe.es/diario_boe/",
        ],
        "AT": [
            "https://www.dsb.gv.at/",
            "https://www.fma.gv.at/en/news/",
        ],
        "BE": [
            "https://www.dataprotectionauthority.be/citizen/news",
            "https://www.nbb.be/en/payments-and-securities/payment-standards/banking-standards",
        ],
        "SE": [
            "https://www.imy.se/en/news/",
            "https://www.fi.se/en/our-registers/news/",
        ],
        "IE": [
            "https://www.dataprotection.ie/en/news-media",
            "https://www.centralbank.ie/regulation/industry-market-sectors/fintech",
        ],
        "LU": [
            "https://cnpd.public.lu/en/actualites.html",
        ],
        "DK": [
            "https://www.datatilsynet.dk/english/news",
        ],
        "FI": [
            "https://tietosuoja.fi/en/frontpage",
        ],
        "PT": [
            "https://www.cnpd.pt/home/noticias.htm",
        ],
        "CZ": [
            "https://www.uoou.cz/en/",
        ],
        "HU": [
            "https://naih.hu/en",
        ],
        "RO": [
            "https://www.dataprotection.ro/?page=Noutati",
        ],
    }

    industry_urls = {
        "DE": {
            "fintech": ["https://www.bafin.de/EN/Aufsicht/FinTech/fintech_node_en.html"],
            "healthcare": ["https://www.bfarm.de/EN/Home/_node.html"],
        },
        "PL": {
            "fintech": ["https://www.knf.gov.pl/en/"],
            "healthcare": ["https://www.gov.pl/web/zdrowie"],
        },
        "FR": {
            "fintech": ["https://acpr.banque-france.fr/en/fintech"],
        },
        "NL": {
            "fintech": ["https://www.afm.nl/en/nieuws"],
        },
        "IE": {
            "fintech": ["https://www.centralbank.ie/regulation/industry-market-sectors/fintech"],
        },
    }

    urls = base_urls.get(country, []).copy()
    country_industry = industry_urls.get(country, {})
    urls.extend(country_industry.get(industry, []))

    return urls
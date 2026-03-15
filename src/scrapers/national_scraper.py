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
            "https://www.bsi.bund.de/SiteGlobals/Forms/Suche/Expertensuche_Pressemitteilungen_und_KM_Formular.html?nn=133020&cl2Categories_DocType=news+pressrelease&sortOrder=dateOfIssue_dt+desc",
        ],
        "PL": [
            "https://dziennikustaw.gov.pl/DU",
            "https://legislacja.gov.pl/",
            "https://uodo.gov.pl/pl/138"
        ],
        "FR": [
            "https://www.legifrance.gouv.fr/",
            "https://www.service-public.gouv.fr/",
            "https://www.cnil.fr/fr/actualite",
            "https://www.amf-france.org/fr/actualites-publications/actualites"
        ],
        "CH": [
            "https://www.admin.ch/gov/en/start/documentation/media-releases.html",
            "https://www.seco.admin.ch/seco/de/home.html",
            "https://www.edoeb.admin.ch/de/mitteilungen"
        ],
        "NL": [
            "https://wetten.overheid.nl/zoeken",
            "https://www.autoriteitpersoonsgegevens.nl/en/news",
            "https://www.dnb.nl/en/general-news/?p=1&l=10"
        ],
        "IT": [
            "https://www.gazzettaufficiale.it/home",
            "https://www.garanteprivacy.it/home/",
            "https://www.bancaditalia.it/media/notizie/index.html"
        ],
        "ES": [
            "https://www.aepd.es/en/press-and-communication/press-releases",
            "https://www.boe.es/diario_boe/",
        ],
        "AT": [
            "https://dsb.gv.at/aktuelles/aktuelles",
            "https://www.fma.gv.at/category/news/?cat=41",
        ],
        "BE": [
            "https://www.dataprotectionauthority.be/citizen/news",
            "https://www.nbb.be/en/news-events/news/press-releases",
        ],
        "SE": [
            "https://www.imy.se/en/news/",
            "https://www.fi.se/en/published/all-published-material/",
        ],
        "IE": [
            "https://www.dataprotection.ie/en/news-media",
            "https://www.centralbank.ie/news-media/press-releases",
        ],
        "LU": [
            "https://cnpd.public.lu/en/actualites.html",
        ],
        "DK": [
            "https://www.datatilsynet.dk/english/",
        ],
        "FI": [
            "https://tietosuoja.fi/en/home",
        ],
        "PT": [
            "https://www.cnpd.pt/",
        ],
        "CZ": [
            "https://uoou.gov.cz/en/news",
        ],
        "HU": [
            "https://naih.hu/",
        ],
        "RO": [
            "https://www.dataprotection.ro/?page=allnews",
        ],
    }

    industry_urls = {
        "DE": {
            "fintech": ["https://www.bafin.de/EN/Homepage/homepage_node.html"],
            "healthcare": ["https://www.bfarm.de/DE/Aktuelles/Presse/Pressemitteilungen/_node.html"],
        },
        "PL": {
            "fintech": [
                "https://www.knf.gov.pl/en/",
            ],
        },
    }

    urls = base_urls.get(country, []).copy()
    country_industry = industry_urls.get(country, {})
    urls.extend(country_industry.get(industry, []))

    return urls
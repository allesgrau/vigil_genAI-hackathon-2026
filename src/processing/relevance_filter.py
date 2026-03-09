import math
from typing import List


def filter_relevant(chunks: List[dict], company_profile: dict, top_k: int = 20) -> List[dict]:
    """
    Filters chunks for relevance to the company profile.
    Uses a combination of keyword matching + cosine similarity.
    """

    if not chunks:
        print("No chunks to filter")
        return []

    industry = company_profile.get("industry", "").lower()
    country = company_profile.get("country", "").lower()
    areas = [a.lower() for a in company_profile.get("areas_of_concern", [])]

    # Build keywords list based on industry, country, and areas of concern
    keywords = _build_keywords(industry, country, areas)

    print(f"🔍 Filtering {len(chunks)} chunks with keywords: {keywords}")

    # Score each chunk and keep those with score > 0
    scored = []
    for chunk in chunks:
        score = _score_chunk(chunk, keywords, areas)
        if score > 0:
            chunk["relevance_score"] = score
            scored.append(chunk)

    # Sort by relevance score and take top_k
    scored.sort(key=lambda x: x["relevance_score"], reverse=True)
    result = scored[:top_k]

    print(f"Filtered to {len(result)} relevant chunks (from {len(chunks)})")
    return result


def _build_keywords(industry: str, country: str, areas: List[str]) -> List[str]:
    """
    Builds a list of keywords based on the company's industry, country, and areas of concern.
    """

    keywords = ["regulation", "directive", "compliance", "obligation",
                "requirement", "enforcement", "penalty", "deadline"]

    industry_keywords = {
        "fintech": ["financial", "payment", "banking", "transaction",
                    "capital", "credit", "investment", "fund"],
        "healthcare": ["medical", "health", "patient", "clinical",
                       "pharmaceutical", "device", "treatment"],
        "ecommerce": ["consumer", "product", "delivery", "return",
                      "marketplace", "seller", "buyer"],
        "saas": ["software", "data", "processing", "cloud",
                 "digital", "platform", "service"],
        "manufacturing": ["product", "safety", "standard", "quality",
                          "import", "export", "supply chain"],
    }

    country_keywords = {
        "de": ["germany", "german", "bundesrat", "bundestag"],
        "pl": ["poland", "polish", "sejm"],
        "fr": ["france", "french"],
        "ch": ["switzerland", "swiss"],
        "nl": ["netherlands", "dutch"],
    }

    keywords.extend(industry_keywords.get(industry, []))
    keywords.extend(country_keywords.get(country, []))
    keywords.extend(areas)

    return list(set(keywords))


def _score_chunk(chunk: dict, keywords: List[str], areas: List[str]) -> float:
    """
    Scores a chunk based on:
    - Keyword matching in content (weight 1.0)
    - Keyword matching in title (weight 2.0 — title is more important)
    - Presence of area of concern (weight 3.0 — most important)
    - Freshness of the document (weight 1.5)
    """

    content = chunk.get("content", "").lower()
    title = chunk.get("title", "").lower()
    score = 0.0

    # Keyword matching in content
    for keyword in keywords:
        if keyword.lower() in content:
            score += 1.0

    # Keyword matching in title
    for keyword in keywords:
        if keyword.lower() in title:
            score += 2.0

    # Presence of area of concern
    for area in areas:
        if area.lower() in content:
            score += 3.0
        if area.lower() in title:
            score += 5.0

    # Normalize score by content length to avoid bias towards longer documents
    content_length = max(len(content.split()), 1)
    normalized_score = score / math.log(content_length + 1)

    return normalized_score
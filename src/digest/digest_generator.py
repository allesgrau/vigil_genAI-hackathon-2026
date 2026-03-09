import os
import requests
import json
from typing import List
from apify_client import ApifyClient
from rag.prompt_templates import get_digest_prompt, get_plain_language_prompt


def generate_digest(chunks: List[dict], company_profile: dict, client: ApifyClient) -> dict:
    """
    Generates a weekly regulatory digest using LLM via OpenRouter.
    """

    if not chunks:
        return _empty_digest(company_profile)

    # Build context from retrieved chunks
    context = _build_context(chunks)
    print(f"Building digest from {len(chunks)} chunks ({len(context)} chars of context)")

    # Generate digest through LLM
    prompt = get_digest_prompt(company_profile, context)
    digest_text = _call_llm(prompt, client, max_tokens=2000)

    if not digest_text:
        print("LLM returned empty digest, using fallback")
        return _fallback_digest(chunks, company_profile)

    # Generate plain language summaries for top relevant chunks
    plain_summaries = []
    for chunk in chunks[:5]:
        plain_prompt = get_plain_language_prompt(
            chunk.get("content", "")[:1000],
            company_profile
        )
        summary = _call_llm(plain_prompt, client, max_tokens=300)
        if summary:
            plain_summaries.append({
                "title": chunk.get("title", "Unknown"),
                "url": chunk.get("url", ""),
                "source": chunk.get("source", ""),
                "plain_summary": summary,
                "relevance_score": chunk.get("relevance_score", 0)
            })

    print("Digest generated successfully")

    return {
        "digest_text": digest_text,
        "plain_summaries": plain_summaries,
        "sources_used": len(chunks),
        "company": company_profile.get("company_name", ""),
        "industry": company_profile.get("industry", ""),
        "country": company_profile.get("country", ""),
    }


def _call_llm(prompt: str, client: ApifyClient, max_tokens: int = 1000) -> str | None:
    """
    Calls the LLM to generate text based on the provided prompt.
    First tries through Apify OpenRouter Actor, then falls back to direct API call if needed.
    """

    # Method 1: Direct API call to OpenRouter Actor (faster if available)
    try:
        actor_url = os.getenv("OPENROUTER_ACTOR_URL", "")

        if actor_url:
            response = requests.post(
                actor_url,
                json={
                    "endpoint": "/chat/completions",
                    "payload": {
                        "model": "anthropic/claude-3-haiku",
                        "max_tokens": max_tokens,
                        "messages": [
                            {"role": "user", "content": prompt}
                        ]
                    }
                },
                timeout=60
            )

            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"]
            else:
                print(f"OpenRouter Actor error: {response.status_code}")

    except Exception as e:
        print(f"OpenRouter Actor failed: {e}")

    # Method 2: Through Apify Actor run (fallback)
    try:
        run = client.actor("apify/openrouter").call(
            run_input={
                "model": "anthropic/claude-3-haiku",
                "max_tokens": max_tokens,
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            }
        )

        dataset = client.dataset(run["defaultDatasetId"])
        items = list(dataset.iterate_items())

        if items:
            return items[0].get("content", "")

    except Exception as e:
        print(f"Apify Actor run failed: {e}")

    return None


def _build_context(chunks: List[dict]) -> str:
    """
    Builds a context string from chunks for the LLM.
    Each chunk is separated by a delimiter with metadata.
    """

    context_parts = []

    for i, chunk in enumerate(chunks):
        title = chunk.get("title", "Unknown Document")
        url = chunk.get("url", "")
        source = chunk.get("source", "")
        content = chunk.get("content", "")[:800]  # limit per chunk

        context_parts.append(
            f"--- Document {i+1}: {title} ---\n"
            f"Source: {source} | URL: {url}\n"
            f"{content}\n"
        )

    return "\n".join(context_parts)


def _empty_digest(company_profile: dict) -> dict:
    """
    Returns an empty digest when no documents are found.
    """

    return {
        "digest_text": (
            f"## Weekly Digest for {company_profile.get('company_name', 'Your Company')}\n\n"
            "No regulatory updates found for your profile this week. "
            "This may indicate no changes in your monitored areas, "
            "or that the sources were temporarily unavailable.\n\n"
            "**Recommendation:** Check back next week or broaden your areas of concern."
        ),
        "plain_summaries": [],
        "sources_used": 0,
        "company": company_profile.get("company_name", ""),
        "industry": company_profile.get("industry", ""),
        "country": company_profile.get("country", ""),
    }


def _fallback_digest(chunks: List[dict], company_profile: dict) -> dict:
    """
    Simple fallback digest when LLM is unavailable.
    Generates a basic summary without AI.
    """

    summaries = []
    for chunk in chunks[:5]:
        summaries.append(
            f"- **{chunk.get('title', 'Unknown')}** "
            f"([source]({chunk.get('url', '#')}))\n"
            f"  {chunk.get('content', '')[:200]}..."
        )

    digest_text = (
        f"## Weekly Digest for {company_profile.get('company_name', 'Your Company')}\n\n"
        f"**Note:** AI summary unavailable. Showing raw regulatory updates.\n\n"
        f"### Recent Updates Found:\n\n" +
        "\n".join(summaries)
    )

    return {
        "digest_text": digest_text,
        "plain_summaries": [],
        "sources_used": len(chunks),
        "company": company_profile.get("company_name", ""),
        "industry": company_profile.get("industry", ""),
        "country": company_profile.get("country", ""),
    }
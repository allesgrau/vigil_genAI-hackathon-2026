import os
import requests
from typing import List
from rag.vector_store import VectorStore
from openai import OpenAI


def retrieve(chunks: List[dict], company_profile: dict, top_k: int = 10) -> List[dict]:
    """
    Main retrieval function – builds vector store, generates query embedding,
    and returns the most relevant chunks.
    """

    if not chunks:
        print("No chunks to retrieve from")
        return []

    # Build vector store from filtered chunks
    store = VectorStore()
    store.add_chunks(chunks)

    # Build query from company profile
    query = _build_query(company_profile)
    print(f"Retrieval query: {query}")

    # Get embedding for query
    query_embedding = _get_query_embedding(query)

    # Choose search method
    if query_embedding:
        print("Using semantic similarity search...")
        results = store.similarity_search(query_embedding, top_k=top_k)
    else:
        print("Falling back to keyword search...")
        keywords = _extract_keywords(company_profile)
        results = store.keyword_search(keywords, top_k=top_k)

    print(f"Retrieved {len(results)} chunks for LLM context")
    return results


def _build_query(company_profile: dict) -> str:
    """
    Builds a natural language query from the company profile.
    This query will be used for semantic search.
    """

    company = company_profile.get("company_name", "a company")
    industry = company_profile.get("industry", "general")
    country = company_profile.get("country", "EU")
    areas = company_profile.get("areas_of_concern", [])
    areas_str = ", ".join(areas) if areas else "general compliance"

    query = (
        f"Recent regulatory changes and compliance requirements "
        f"for a {industry} company based in {country}, "
        f"specifically regarding {areas_str}. "
        f"Deadlines, obligations, penalties, and enforcement updates."
    )

    return query


def _get_query_embedding(query: str) -> List[float] | None:
    
    try:
        client = OpenAI(
            base_url=os.getenv("OPENROUTER_ACTOR_URL", "https://openrouter.apify.actor/api/v1"),
            api_key="no-key-required-but-must-not-be-empty",
            default_headers={
                "Authorization": f"Bearer {os.getenv('APIFY_TOKEN', '')}"
            }
        )

        response = client.embeddings.create(
            model="openai/text-embedding-3-small",
            input=query
        )
        return response.data[0].embedding

    except Exception as e:
        print(f"⚠️ Query embedding error: {e}")
        return None


def _extract_keywords(company_profile: dict) -> List[str]:
    """
    Extracts keywords from the company profile for fallback keyword search.
    """

    keywords = []

    keywords.append(company_profile.get("industry", ""))
    keywords.append(company_profile.get("country", ""))
    keywords.extend(company_profile.get("areas_of_concern", []))

    keywords.extend([
        "regulation", "compliance", "deadline",
        "obligation", "penalty", "enforcement"
    ])

    return [k for k in keywords if k]
# tests/test_vigil.py
"""
Vigil Integration Tests
Real API calls, minimal data — same philosophy as test_mode.
Run: pytest tests/test_vigil.py -v
"""

import os
import sys
import pytest
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from apify_client import ApifyClient
from processing.chunker import chunk_documents
from processing.fact_extractor import extract_facts
from processing.embedder import embed_facts
from processing.relevance_filter import filter_relevant
from rag.retriever import retrieve
from digest.digest_generator import generate_digest
from digest.alert_engine import generate_alerts
from digest.formatter import format_output


# ─── FIXTURES ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def apify_client():
    token = os.getenv("APIFY_TOKEN")
    assert token, "APIFY_TOKEN not set in .env"
    return ApifyClient(token=token)


@pytest.fixture(scope="session")
def company_profile():
    return {
        "company_name": "TestCorp",
        "industry": "fintech",
        "country": "DE",
        "size": "startup",
        "areas_of_concern": ["GDPR", "DORA"],
        "test_mode": True
    }


@pytest.fixture(scope="session")
def sample_documents(apify_client):
    """Scrape 1 real page from EDPB — lightweight, ~$0.02"""
    run = apify_client.actor("apify/website-content-crawler").call(
        run_input={
            "startUrls": [{"url": "https://edpb.europa.eu/news/news_en"}],
            "maxCrawlDepth": 0,
            "maxCrawlPages": 1,
            "outputFormats": ["markdown"],
        },
        memory_mbytes=2048
    )
    items = list(apify_client.dataset(run["defaultDatasetId"]).iterate_items())
    assert len(items) > 0, "Scraper returned 0 documents"
    return [{"content": i.get("text", i.get("markdown", "")),
             "url": i.get("url", ""),
             "title": i.get("title", ""),
             "source": "edpb"} for i in items]


# ─── CHUNKER ──────────────────────────────────────────────────────────────────

class TestChunker:

    def test_chunks_non_empty_documents(self, sample_documents):
        chunks = chunk_documents(sample_documents)
        assert len(chunks) > 0, "Should produce at least 1 chunk"

    def test_chunk_has_required_fields(self, sample_documents):
        chunks = chunk_documents(sample_documents)
        required = {"chunk_id", "content", "url", "title", "source", "chunk_index"}
        for chunk in chunks:
            assert required.issubset(chunk.keys()), f"Missing fields: {required - chunk.keys()}"

    def test_chunk_content_not_empty(self, sample_documents):
        chunks = chunk_documents(sample_documents)
        for chunk in chunks:
            assert len(chunk["content"]) > 0, "Chunk content should not be empty"

    def test_chunk_size_respected(self, sample_documents):
        chunks = chunk_documents(sample_documents, chunk_size=500)
        # Chunks can slightly exceed due to overlap — allow 2x tolerance
        for chunk in chunks:
            assert len(chunk["content"]) < 1200, "Chunk way too large"

    def test_empty_documents_returns_empty(self):
        chunks = chunk_documents([])
        assert chunks == []

    def test_document_without_content_skipped(self):
        docs = [{"content": "", "url": "http://x.com", "title": "Empty"}]
        chunks = chunk_documents(docs)
        assert chunks == []


# ─── FACT EXTRACTOR ───────────────────────────────────────────────────────────

class TestFactExtractor:

    def test_extracts_facts_from_real_chunks(self, sample_documents, company_profile):
        chunks = chunk_documents(sample_documents)[:5]  # tylko 5 chunków
        facts = extract_facts(chunks, company_profile)
        assert isinstance(facts, list), "Should return a list"
        assert len(facts) > 0, "Should extract at least 1 fact"

    def test_fact_has_required_fields(self, sample_documents, company_profile):
        chunks = chunk_documents(sample_documents)[:5]
        facts = extract_facts(chunks, company_profile)
        required = {"claim", "regulation", "severity", "source_url", "keywords"}
        for fact in facts:
            assert required.issubset(fact.keys()), f"Missing: {required - fact.keys()}"

    def test_fact_claim_not_empty(self, sample_documents, company_profile):
        chunks = chunk_documents(sample_documents)[:5]
        facts = extract_facts(chunks, company_profile)
        for fact in facts:
            assert fact["claim"], "Claim should not be empty"

    def test_fact_severity_valid(self, sample_documents, company_profile):
        chunks = chunk_documents(sample_documents)[:5]
        facts = extract_facts(chunks, company_profile)
        valid = {"critical", "high", "medium", "low"}
        for fact in facts:
            assert fact["severity"] in valid, f"Invalid severity: {fact['severity']}"

    def test_empty_chunks_returns_empty(self, company_profile):
        facts = extract_facts([], company_profile)
        assert facts == []


# ─── EMBEDDER + FILTER ────────────────────────────────────────────────────────

class TestEmbedderAndFilter:

    def test_embed_facts_adds_embeddings(self, sample_documents, company_profile):
        chunks = chunk_documents(sample_documents)[:3]
        facts = extract_facts(chunks, company_profile)
        if not facts:
            pytest.skip("No facts extracted")
        embedded = embed_facts(facts)
        assert len(embedded) == len(facts)
        for f in embedded:
            assert f.get("embedding") is not None, "Embedding should not be None"
            assert len(f["embedding"]) > 0, "Embedding should not be empty"

    def test_filter_returns_subset(self, sample_documents, company_profile):
        chunks = chunk_documents(sample_documents)[:3]
        facts = extract_facts(chunks, company_profile)
        if not facts:
            pytest.skip("No facts extracted")
        embedded = embed_facts(facts)
        relevant = filter_relevant(embedded, company_profile)
        assert len(relevant) <= len(embedded), "Filter should not add facts"

    def test_filter_returns_list(self, sample_documents, company_profile):
        chunks = chunk_documents(sample_documents)[:3]
        facts = extract_facts(chunks, company_profile)
        if not facts:
            pytest.skip("No facts extracted")
        embedded = embed_facts(facts)
        relevant = filter_relevant(embedded, company_profile)
        assert isinstance(relevant, list)


# ─── DIGEST GENERATOR ─────────────────────────────────────────────────────────

class TestDigestGenerator:

    def test_generates_digest_from_real_facts(self, sample_documents, company_profile, apify_client):
        chunks = chunk_documents(sample_documents)[:5]
        facts = extract_facts(chunks, company_profile)
        if not facts:
            pytest.skip("No facts extracted")
        embedded = embed_facts(facts)
        relevant = filter_relevant(embedded, company_profile)
        retrieved = retrieve(relevant, company_profile)
        digest = generate_digest(retrieved, company_profile, apify_client)
        assert digest.get("digest_text"), "Digest text should not be empty"

    def test_digest_has_required_keys(self, sample_documents, company_profile, apify_client):
        chunks = chunk_documents(sample_documents)[:5]
        facts = extract_facts(chunks, company_profile)
        if not facts:
            pytest.skip("No facts extracted")
        embedded = embed_facts(facts)
        relevant = filter_relevant(embedded, company_profile)
        retrieved = retrieve(relevant, company_profile)
        digest = generate_digest(retrieved, company_profile, apify_client)
        required = {"digest_text", "plain_summaries", "sources_used", "company"}
        assert required.issubset(digest.keys())

    def test_empty_chunks_returns_empty_digest(self, company_profile, apify_client):
        digest = generate_digest([], company_profile, apify_client)
        assert "digest_text" in digest
        assert digest["sources_used"] == 0

    def test_digest_no_past_deadlines(self, sample_documents, company_profile, apify_client):
        """Deadliny w digestcie nie mogą być przed 2026."""
        from datetime import datetime
        import re
        chunks = chunk_documents(sample_documents)[:5]
        facts = extract_facts(chunks, company_profile)
        if not facts:
            pytest.skip("No facts extracted")
        embedded = embed_facts(facts)
        relevant = filter_relevant(embedded, company_profile)
        retrieved = retrieve(relevant, company_profile)
        digest = generate_digest(retrieved, company_profile, apify_client)
        text = digest.get("digest_text", "")
        years = re.findall(r'\b(20\d{2})\b', text)
        past_years = [y for y in years if int(y) < datetime.now().year]
        assert not past_years, f"Found past years in digest: {past_years}"


# ─── FORMATTER ────────────────────────────────────────────────────────────────

class TestFormatter:

    def test_format_output_has_all_keys(self, company_profile):
        digest = {
            "digest_text": "## Test digest",
            "plain_summaries": [],
            "sources_used": 3,
            "company": "TestCorp",
            "industry": "fintech",
            "country": "DE",
        }
        alerts = []
        output = format_output(digest, alerts, company_profile)
        required = {
            "generated_at", "company_name", "sources_analyzed",
            "alerts_count", "critical_alerts", "high_alerts",
            "digest_markdown", "full_report_markdown", "status"
        }
        assert required.issubset(output.keys())

    def test_format_output_counts_alerts_correctly(self, company_profile):
        digest = {"digest_text": "test", "plain_summaries": [], "sources_used": 1,
                  "company": "X", "industry": "Y", "country": "Z"}
        alerts = [
            {"severity": "critical", "title": "A"},
            {"severity": "high", "title": "B"},
            {"severity": "medium", "title": "C"},
        ]
        output = format_output(digest, alerts, company_profile)
        assert output["alerts_count"] == 3
        assert len(output["critical_alerts"]) == 1
        assert len(output["high_alerts"]) == 1
        assert len(output["medium_alerts"]) == 1

    def test_format_output_status_success(self, company_profile):
        digest = {"digest_text": "something", "plain_summaries": [], "sources_used": 1,
                  "company": "X", "industry": "Y", "country": "Z"}
        output = format_output(digest, [], company_profile)
        assert output["status"] == "success"

    def test_format_output_status_partial_when_empty(self, company_profile):
        digest = {"digest_text": "", "plain_summaries": [], "sources_used": 0,
                  "company": "X", "industry": "Y", "country": "Z"}
        output = format_output(digest, [], company_profile)
        assert output["status"] == "partial"
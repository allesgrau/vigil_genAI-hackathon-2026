import streamlit as st
import asyncio
import sys
import os
from dotenv import load_dotenv
import json
import hashlib

load_dotenv()
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from apify_client import ApifyClient
from scrapers.eurlex_scraper import scrape_eurlex
from scrapers.gdpr_scraper import scrape_gdpr
from scrapers.national_scraper import scrape_national
from processing.chunker import chunk_documents
from processing.embedder import embed_chunks
from processing.relevance_filter import filter_relevant
from rag.retriever import retrieve
from digest.digest_generator import generate_digest
from digest.alert_engine import generate_alerts
from digest.formatter import format_output

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="Vigil — Regulatory Intelligence",
    page_icon="🛡️",
    layout="wide"
)

# --- CUSTOM CSS ---
st.markdown("""
<style>
    .main { background-color: #0f1117; }
    .stApp { background-color: #0f1117; }
    .vigil-header {
        background: linear-gradient(135deg, #1B2A4A 0%, #2d4a7a 100%);
        padding: 2rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        text-align: center;
    }
    .alert-critical {
        background-color: #2d1515;
        border-left: 4px solid #ff4444;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
    }
    .alert-high {
        background-color: #2d2015;
        border-left: 4px solid #ff8800;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
    }
    .alert-medium {
        background-color: #2d2d15;
        border-left: 4px solid #ffcc00;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
    }
    .summary-card {
        background-color: #1a1f2e;
        border: 1px solid #2d3748;
        padding: 1.2rem;
        border-radius: 10px;
        margin: 0.5rem 0;
    }
    .metric-card {
        background-color: #1a1f2e;
        border: 1px solid #2d3748;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

def _profile_hash(company_profile: dict) -> str:
    key = f"{company_profile['industry']}_{company_profile['country']}_{sorted(company_profile['areas_of_concern'])}"
    return hashlib.md5(key.encode()).hexdigest()[:8]

def _cache_path(company_profile: dict) -> str:
    return f"cache_{_profile_hash(company_profile)}.json"

def _load_cache(company_profile: dict) -> dict | None:
    path = _cache_path(company_profile)
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return None

def _save_cache(company_profile: dict, output: dict):
    path = _cache_path(company_profile)
    with open(path, "w") as f:
        json.dump(output, f)

async def run_vigil(company_profile: dict) -> dict:
    client = ApifyClient(token=os.getenv("APIFY_TOKEN"))
    test_mode = company_profile.get("test_mode", True)

    with st.status("🔍 Vigil is working...", expanded=True) as status:
        st.write("📡 Scraping regulatory sources...")
        eurlex_docs = await scrape_eurlex(client, company_profile, test_mode=test_mode)
        gdpr_docs = await scrape_gdpr(client, company_profile, test_mode=test_mode)
        national_docs = await scrape_national(client, company_profile, test_mode=test_mode)
        raw_documents = eurlex_docs + gdpr_docs + national_docs
        st.write(f"✅ Scraped {len(raw_documents)} documents")

        st.write("✂️ Chunking documents...")
        chunks = chunk_documents(raw_documents)
        st.write(f"✅ Created {len(chunks)} chunks")

        st.write("🧠 Embedding and filtering...")
        embedded = embed_chunks(chunks)
        relevant = filter_relevant(embedded, company_profile)
        st.write(f"✅ Found {len(relevant)} relevant chunks")

        st.write("🔎 Retrieving and generating digest...")
        retrieved = retrieve(relevant, company_profile)
        digest = generate_digest(retrieved, company_profile, client)
        alerts = generate_alerts(retrieved, company_profile)
        st.write("✅ Digest generated!")

        status.update(label="✅ Vigil complete!", state="complete")

    return format_output(digest, alerts, company_profile)


def render_alerts(output: dict):
    st.subheader("🚨 Alerts")

    critical = output.get("critical_alerts", [])
    high = output.get("high_alerts", [])
    medium = output.get("medium_alerts", [])

    if not critical and not high and not medium:
        st.success("✅ No urgent alerts this week!")
        return

    for alert in critical:
        st.markdown(f"""
        <div class="alert-critical">
            🔴 <strong>{alert.get('title', 'Unknown')}</strong><br>
            📅 Deadline: <code>{alert.get('deadline', 'Check source')}</code><br>
            ⚡ Action: {alert.get('action_required', '')}<br>
            🔗 <a href="{alert.get('source_url', '#')}" target="_blank">Source</a>
        </div>
        """, unsafe_allow_html=True)

    for alert in high:
        st.markdown(f"""
        <div class="alert-high">
            🟠 <strong>{alert.get('title', 'Unknown')}</strong><br>
            📅 Deadline: <code>{alert.get('deadline', 'Check source')}</code><br>
            ⚡ Action: {alert.get('action_required', '')}<br>
            🔗 <a href="{alert.get('source_url', '#')}" target="_blank">Source</a>
        </div>
        """, unsafe_allow_html=True)

    for alert in medium:
        st.markdown(f"""
        <div class="alert-medium">
            🟡 <strong>{alert.get('title', 'Unknown')}</strong><br>
            📅 Deadline: <code>{alert.get('deadline', 'Check source')}</code><br>
            ⚡ Action: {alert.get('action_required', '')}<br>
            🔗 <a href="{alert.get('source_url', '#')}" target="_blank">Source</a>
        </div>
        """, unsafe_allow_html=True)


def render_plain_summaries(output: dict):
    summaries = output.get("plain_summaries", [])
    if not summaries:
        st.info("No plain language summaries available.")
        return

    for i, summary in enumerate(summaries, 1):
        with st.expander(f"📄 Document {i} — {summary.get('source', '').upper()}"):
            st.markdown(summary.get("plain_summary", ""))
            st.caption(f"🔗 {summary.get('url', '')}")


# --- MAIN APP ---
st.markdown("""
<div class="vigil-header">
    <h1>🛡️ Vigil</h1>
    <p style="color: #a0aec0; font-size: 1.1rem;">
        AI-powered regulatory intelligence for European SMEs
    </p>
</div>
""", unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://em-content.zobj.net/source/apple/391/shield_1f6e1-fe0f.png", width=80)
    st.title("Company Profile")
    st.caption("Fill in your company details to get personalized regulatory intelligence.")

    company_name = st.text_input("Company Name", value="TechStartup GmbH")

    industry = st.selectbox("Industry", [
        "fintech", "healthcare", "ecommerce", "saas", "manufacturing"
    ])

    country = st.selectbox("Country", [
        "DE", "PL", "FR", "CH", "NL", "IT", "ES", "AT", "BE", "SE"
    ])

    size = st.selectbox("Company Size", ["startup", "sme", "enterprise"])

    areas = st.multiselect(
        "Regulatory Areas to Monitor",
        ["GDPR", "AI Act", "PSD2", "AML", "NIS2", "DORA"],
        default=["GDPR", "AI Act"]
    )

    test_mode = st.toggle("⚡ Fast Mode (for testing)", value=True)

    st.divider()
    run_button = st.button("🚀 Generate Digest", type="primary", use_container_width=True)

# --- MAIN CONTENT ---
if run_button:
    if not areas:
        st.warning("Please select at least one regulatory area to monitor.")
    else:
        company_profile = {
            "company_name": company_name,
            "industry": industry,
            "country": country,
            "size": size,
            "areas_of_concern": areas,
            "test_mode": test_mode
        }

        cached = _load_cache(company_profile)
        if cached and test_mode:
            st.info("⚡ Loaded from cache — instant results!")
            output = cached
        else:
            output = asyncio.run(run_vigil(company_profile))
            _save_cache(company_profile, output)

        # Metrics row
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📚 Sources Analyzed", output.get("sources_analyzed", 0))
        with col2:
            st.metric("🚨 Total Alerts", output.get("alerts_count", 0))
        with col3:
            st.metric("🔴 Critical", len(output.get("critical_alerts", [])))
        with col4:
            st.metric("🟠 High Priority", len(output.get("high_alerts", [])))

        st.divider()

        # Two columns layout
        col_left, col_right = st.columns([3, 2])

        with col_left:
            st.subheader("📋 Weekly Digest")
            st.markdown(output.get("digest_markdown", ""))

            st.divider()
            st.subheader("🗣️ Plain Language Summaries")
            render_plain_summaries(output)

        with col_right:
            render_alerts(output)

            st.divider()
            st.subheader("📥 Download Report")
            st.download_button(
                label="⬇️ Download Full Report (Markdown)",
                data=output.get("full_report_markdown", ""),
                file_name=f"vigil_digest_{output.get('company_name', 'report').replace(' ', '_')}.md",
                mime="text/markdown",
                use_container_width=True
            )

else:
    # Landing state
    st.markdown("""
    ### 👈 Fill in your company profile to get started

    Vigil monitors EU regulatory sources in real time and delivers:

    - 📋 **Weekly digest** of relevant regulatory changes
    - 🚨 **Urgent alerts** when deadlines are approaching
    - 🗣️ **Plain language summaries** — no legal jargon
    - 💡 **Strategic insights** for your business
    - 📥 **Downloadable reports**

    **Sources monitored:** EUR-Lex · EDPB · National regulators · GDPR.eu
    """)

    st.info("💡 Built at GenAI Zurich Hackathon 2026 🇨🇭")
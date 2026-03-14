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
from processing.fact_extractor import extract_facts
from processing.embedder import embed_facts
from processing.relevance_filter import filter_relevant
from rag.retriever import retrieve
from digest.digest_generator import generate_digest
from digest.alert_engine import generate_alerts
from digest.formatter import format_output

st.set_page_config(
    page_title="Vigil — Regulatory Intelligence",
    page_icon="🛡️",
    layout="wide"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    .stApp {
        background: #f8faff;
        color: #1a1f36;
    }

    section[data-testid="stSidebar"] {
        background: #ffffff;
        border-right: 1px solid #e8edf5;
    }

    .hero-section {
        background: linear-gradient(135deg, #f0f4ff 0%, #e8f0fe 40%, #dbeafe 100%);
        border-radius: 20px;
        padding: 4rem 3rem;
        margin-bottom: 2rem;
        position: relative;
        overflow: hidden;
    }

    .hero-blob {
        position: absolute;
        width: 400px;
        height: 400px;
        border-radius: 50%;
        filter: blur(80px);
        opacity: 0.4;
        top: -100px;
        right: -100px;
        background: radial-gradient(circle, #93c5fd, #6366f1);
    }

    .hero-blob-2 {
        position: absolute;
        width: 300px;
        height: 300px;
        border-radius: 50%;
        filter: blur(60px);
        opacity: 0.3;
        bottom: -80px;
        left: 200px;
        background: radial-gradient(circle, #bfdbfe, #a5b4fc);
    }

    .hero-badge {
        display: inline-block;
        background: #eff6ff;
        border: 1px solid #bfdbfe;
        color: #3b82f6;
        font-size: 0.8rem;
        font-weight: 600;
        padding: 0.3rem 0.9rem;
        border-radius: 100px;
        margin-bottom: 1.5rem;
        letter-spacing: 0.05em;
    }

    .hero-title {
        font-size: 3.2rem;
        font-weight: 800;
        color: #0f172a;
        line-height: 1.15;
        margin-bottom: 1.2rem;
        letter-spacing: -0.02em;
    }

    .hero-title span {
        background: linear-gradient(135deg, #2563eb, #6366f1);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .hero-subtitle {
        font-size: 1.15rem;
        color: #475569;
        line-height: 1.7;
        max-width: 600px;
        margin-bottom: 2rem;
        font-weight: 400;
    }

    .feature-pill {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        background: white;
        border: 1px solid #e2e8f0;
        color: #334155;
        font-size: 0.85rem;
        font-weight: 500;
        padding: 0.4rem 0.9rem;
        border-radius: 100px;
        margin: 0.2rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }

    .metric-card {
        background: white;
        border: 1px solid #e8edf5;
        border-radius: 14px;
        padding: 1.2rem 1.5rem;
        box-shadow: 0 1px 4px rgba(0,0,0,0.04);
    }

    .alert-critical {
        background: #fff5f5;
        border-left: 4px solid #ef4444;
        border-radius: 10px;
        padding: 1rem 1.2rem;
        margin: 0.6rem 0;
        box-shadow: 0 1px 3px rgba(239,68,68,0.1);
    }

    .alert-high {
        background: #fff8f0;
        border-left: 4px solid #f97316;
        border-radius: 10px;
        padding: 1rem 1.2rem;
        margin: 0.6rem 0;
        box-shadow: 0 1px 3px rgba(249,115,22,0.1);
    }

    .alert-medium {
        background: #fefce8;
        border-left: 4px solid #eab308;
        border-radius: 10px;
        padding: 1rem 1.2rem;
        margin: 0.6rem 0;
    }

    .alert-title {
        font-weight: 700;
        color: #0f172a;
        font-size: 0.95rem;
        margin-bottom: 0.3rem;
    }

    .alert-meta {
        font-size: 0.85rem;
        color: #64748b;
        margin: 0.15rem 0;
    }

    .digest-container {
        background: white;
        border: 1px solid #e8edf5;
        border-radius: 16px;
        padding: 2rem;
        box-shadow: 0 1px 4px rgba(0,0,0,0.04);
    }

    .summary-expander {
        background: white;
        border-radius: 12px;
    }

    .source-badge {
        display: inline-block;
        background: #eff6ff;
        color: #2563eb;
        font-size: 0.75rem;
        font-weight: 600;
        padding: 0.2rem 0.6rem;
        border-radius: 6px;
        margin-bottom: 0.5rem;
    }

    .stButton > button {
        background: linear-gradient(135deg, #2563eb, #6366f1) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        padding: 0.6rem 1.5rem !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 4px 12px rgba(37,99,235,0.3) !important;
    }

    .stButton > button p {
        color: white !important;
    }

    .stButton > button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 16px rgba(37,99,235,0.4) !important;
    }

    div[data-testid="stMetricValue"] {
        color: #0f172a !important;
        font-weight: 700 !important;
    }

    .stInfo {
        background: #eff6ff !important;
        border: 1px solid #bfdbfe !important;
        border-radius: 10px !important;
        color: #1e40af !important;
    }

    h1, h2, h3 {
        color: #0f172a !important;
    }

    .stDivider {
        border-color: #e8edf5 !important;
    }

    section[data-testid="stSidebar"] * {
        color: #1a1f36 !important;
    }

    section[data-testid="stSidebar"] .stTextInput input {
        background: #f8faff !important;
        color: #1a1f36 !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 8px !important;
    }

    section[data-testid="stSidebar"] .stSelectbox > div {
        background: #f8faff !important;
        color: #1a1f36 !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 8px !important;
    }

    section[data-testid="stSidebar"] .stMultiSelect > div {
        background: #f8faff !important;
        color: #1a1f36 !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 8px !important;
    }

    section[data-testid="stSidebar"] label {
        color: #374151 !important;
        font-weight: 500 !important;
    }

    section[data-testid="stSidebar"] .stCaption {
        color: #6b7280 !important;
    }

    section[data-testid="stSidebar"] p {
        color: #374151 !important;
    }
            
    section[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] {
        background-color: #f8faff !important;
    }

    section[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] > div {
        background-color: #f8faff !important;
        color: #1a1f36 !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 8px !important;
    }

    section[data-testid="stSidebar"] .stMultiSelect [data-baseweb="select"] > div {
        background-color: #f8faff !important;
        color: #1a1f36 !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 8px !important;
    }

    section[data-testid="stSidebar"] [data-baseweb="base-input"] {
        background-color: #f8faff !important;
    }

    section[data-testid="stSidebar"] input {
        background-color: #f8faff !important;
        color: #1a1f36 !important;
    }

    [data-baseweb="popover"] {
        background-color: white !important;
    }

    [data-baseweb="menu"] {
        background-color: white !important;
    }

    [data-baseweb="option"] {
        background-color: white !important;
        color: #1a1f36 !important;
    }

    .stButton > button span {
        color: white !important;
    }

    .stButton > button div {
        color: white !important;
    }

    [data-testid="stBaseButton-primary"] {
        color: white !important;
    }

    [data-testid="stBaseButton-primary"] * {
        color: white !important;
    }

    section[data-testid="stSidebar"] .stButton > button,
    section[data-testid="stSidebar"] .stButton > button * {
        color: white !important;
        -webkit-text-fill-color: white !important;
    }

    [data-testid="stDownloadButton"] button,
    [data-testid="stDownloadButton"] button * {
        color: white !important;
        -webkit-text-fill-color: white !important;
        background: linear-gradient(135deg, #2563eb, #6366f1) !important;
    }

    div[data-testid="stMetricLabel"] p,
    div[data-testid="stMetricLabel"] {
        color: #64748b !important;
        -webkit-text-fill-color: #64748b !important;
    }

    div[data-testid="stStatusWidget"] {
        background: #eff6ff !important;
        border: 1px solid #bfdbfe !important;
        border-radius: 12px !important;
        color: #1e40af !important;
    }

    div[data-testid="stStatusWidget"] * {
        color: #1e40af !important;
        -webkit-text-fill-color: #1e40af !important;
    }

    header[data-testid="stHeader"] {
        display: none !important;
    }

    [data-testid="stMetricLabel"] {
        visibility: visible !important;
        color: #64748b !important;
    }

    [data-testid="stMetricLabel"] * {
        color: #64748b !important;
        -webkit-text-fill-color: #64748b !important;
    }
</style>
""", unsafe_allow_html=True)


def _profile_hash(company_profile: dict) -> str:
    key = f"{company_profile['industry']}_{company_profile['country']}_{sorted(company_profile['areas_of_concern'])}"
    return hashlib.md5(key.encode()).hexdigest()[:8]

def _cache_path(company_profile: dict) -> str:
    return f"cache_{_profile_hash(company_profile)}.json"

def _load_cache(company_profile: dict):
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

        st.write("🔬 Extracting facts with AI...")
        facts = extract_facts(chunks, company_profile)
        st.write(f"✅ Extracted {len(facts)} regulatory facts")

        st.write("🧠 Embedding and filtering facts...")
        embedded_facts = embed_facts(facts)
        relevant = filter_relevant(embedded_facts, company_profile)
        st.write(f"✅ Found {len(relevant)} relevant facts")

        st.write("🔎 Generating personalized digest...")
        retrieved = retrieve(relevant, company_profile)
        digest = generate_digest(retrieved, company_profile, client)
        alerts = generate_alerts(retrieved, company_profile)
        st.write("✅ Digest generated!")

        status.update(label="✅ Vigil complete!", state="complete")

    return format_output(digest, alerts, company_profile)


def render_alerts(output: dict):
    critical = output.get("critical_alerts", [])
    high = output.get("high_alerts", [])
    medium = output.get("medium_alerts", [])

    if not critical and not high and not medium:
        st.success("✅ No urgent alerts this week — you're compliant!")
        return

    for alert in critical:
        st.markdown(f"""
        <div class="alert-critical">
            <div class="alert-title">🔴 {alert.get('title', 'Unknown')}</div>
            <div class="alert-meta">📅 Deadline: <strong>{alert.get('deadline', 'Check source')}</strong></div>
            <div class="alert-meta">⚡ {alert.get('action_required', '')}</div>
            <div class="alert-meta">🔗 <a href="{alert.get('source_url', '#')}" target="_blank" style="color:#2563eb;">View source</a></div>
        </div>
        """, unsafe_allow_html=True)

    for alert in high:
        st.markdown(f"""
        <div class="alert-high">
            <div class="alert-title">🟠 {alert.get('title', 'Unknown')}</div>
            <div class="alert-meta">📅 Deadline: <strong>{alert.get('deadline', 'Check source')}</strong></div>
            <div class="alert-meta">⚡ {alert.get('action_required', '')}</div>
            <div class="alert-meta">🔗 <a href="{alert.get('source_url', '#')}" target="_blank" style="color:#2563eb;">View source</a></div>
        </div>
        """, unsafe_allow_html=True)

    for alert in medium:
        st.markdown(f"""
        <div class="alert-medium">
            <div class="alert-title">🟡 {alert.get('title', 'Unknown')}</div>
            <div class="alert-meta">📅 Deadline: <strong>{alert.get('deadline', 'Check source')}</strong></div>
            <div class="alert-meta">⚡ {alert.get('action_required', '')}</div>
            <div class="alert-meta">🔗 <a href="{alert.get('source_url', '#')}" target="_blank" style="color:#2563eb;">View source</a></div>
        </div>
        """, unsafe_allow_html=True)


def render_plain_summaries(output: dict):
    summaries = output.get("plain_summaries", [])
    if not summaries:
        st.info("No plain language summaries available.")
        return

    for i, summary in enumerate(summaries, 1):
        source = summary.get('source', '').upper()
        title = summary.get('title', f'Document {i}')
        with st.expander(f"📄 {title} — {source}"):
            st.markdown(f'<div class="source-badge">{source}</div>', unsafe_allow_html=True)
            st.markdown(summary.get("plain_summary", ""))
            if summary.get('url'):
                st.caption(f"🔗 [{summary.get('url')}]({summary.get('url')})")


# ─── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding: 1rem 0 0.5rem 0;">
        <div style="font-size: 1.8rem; font-weight: 800; color: #0f172a; letter-spacing: -0.02em;">
            🛡️ Vigil
        </div>
        <div style="font-size: 0.8rem; color: #94a3b8; font-weight: 500; margin-top: 0.2rem;">
            Regulatory Intelligence
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    st.markdown("**Company Profile**")
    st.caption("Personalize your regulatory feed")

    company_name = st.text_input("Company Name", value="TechStartup GmbH")

    industry = st.selectbox("Industry", [
        "fintech", "healthcare", "ecommerce", "saas", "manufacturing"
    ])

    country = st.selectbox("Country", [
        "DE", "PL", "FR", "CH", "NL", "IT", "ES", "AT", "BE", "SE"
    ])

    size = st.selectbox("Company Size", ["startup", "sme", "enterprise"])

    areas = st.multiselect(
        "Monitor Regulations",
        ["GDPR", "AI Act", "PSD2", "AML", "NIS2", "DORA"],
        default=["GDPR", "AI Act"]
    )

    test_mode = st.toggle("⚡ Fast Mode", value=True,
                          help="Uses cached results for instant demo")

    st.divider()
    run_button = st.button("🚀 Generate Digest", type="primary", use_container_width=True)

    st.markdown("""
    <div style="margin-top: 2rem; padding: 1rem; background: #f8faff;
                border-radius: 10px; border: 1px solid #e8edf5;">
        <div style="font-size: 0.75rem; color: #94a3b8; font-weight: 600;
                    text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.5rem;">
            Sources monitored
        </div>
        <div style="font-size: 0.82rem; color: #475569; line-height: 1.8;">
            EUR-Lex · EDPB · GDPR.eu<br>
            National regulators (DE, PL, FR…)
        </div>
    </div>
    """, unsafe_allow_html=True)


# ─── MAIN CONTENT ──────────────────────────────────────────────────────────────
if run_button:
    if not areas:
        st.warning("Please select at least one regulatory area.")
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

        # Metrics
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

        col_left, col_right = st.columns([3, 2])

        with col_left:
            st.markdown('<div class="digest-container">', unsafe_allow_html=True)
            st.subheader("📋 Weekly Digest")
            st.markdown(output.get("digest_markdown", ""))
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            st.subheader("🗣️ Plain Language Summaries")
            st.caption("What does this actually mean for your business?")
            render_plain_summaries(output)

        with col_right:
            st.subheader("🚨 Alerts")
            render_alerts(output)

            st.divider()
            st.subheader("📥 Download Report")
            st.download_button(
                label="⬇️ Download Full Report (.md)",
                data=output.get("full_report_markdown", ""),
                file_name=f"vigil_{company_name.replace(' ', '_')}_digest.md",
                mime="text/markdown",
                use_container_width=True
            )

else:
    # ─── LANDING PAGE ──────────────────────────────────────────────────────────
    st.markdown("""
    <div class="hero-section">
        <div class="hero-blob"></div>
        <div class="hero-blob-2"></div>
        <div style="position: relative; z-index: 1;">
            <div class="hero-badge">🇪🇺 Built for European SMEs</div>
            <div class="hero-title">
                Stop paying lawyers<br>to <span>stay compliant.</span>
            </div>
            <div class="hero-subtitle">
                SMEs spend thousands on lawyers just to stay compliant.
                Vigil monitors EU regulations in real time and delivers
                personalized, actionable compliance alerts —
                <strong>before the deadline hits.</strong>
            </div>
            <div>
                <span class="feature-pill">📋 Weekly digests</span>
                <span class="feature-pill">🚨 Deadline alerts</span>
                <span class="feature-pill">🗣️ Plain language</span>
                <span class="feature-pill">💡 Strategic insights</span>
                <span class="feature-pill">📥 Downloadable reports</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        <div style="background: white; border: 1px solid #e8edf5; border-radius: 16px;
                    padding: 1.5rem; box-shadow: 0 1px 4px rgba(0,0,0,0.04);">
            <div style="font-size: 2rem; margin-bottom: 0.8rem;">⚡</div>
            <div style="font-weight: 700; color: #0f172a; margin-bottom: 0.5rem; font-size: 1rem;">
                Real-time monitoring
            </div>
            <div style="color: #64748b; font-size: 0.88rem; line-height: 1.6;">
                Vigil scrapes EUR-Lex, EDPB, and national regulators
                continuously — so you never miss a change.
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div style="background: white; border: 1px solid #e8edf5; border-radius: 16px;
                    padding: 1.5rem; box-shadow: 0 1px 4px rgba(0,0,0,0.04);">
            <div style="font-size: 2rem; margin-bottom: 0.8rem;">🎯</div>
            <div style="font-weight: 700; color: #0f172a; margin-bottom: 0.5rem; font-size: 1rem;">
                Personalized to your business
            </div>
            <div style="color: #64748b; font-size: 0.88rem; line-height: 1.6;">
                Enter your industry, country, and regulatory areas.
                Vigil filters out everything irrelevant.
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("""
        <div style="background: white; border: 1px solid #e8edf5; border-radius: 16px;
                    padding: 1.5rem; box-shadow: 0 1px 4px rgba(0,0,0,0.04);">
            <div style="font-size: 2rem; margin-bottom: 0.8rem;">🗣️</div>
            <div style="font-weight: 700; color: #0f172a; margin-bottom: 0.5rem; font-size: 1rem;">
                No legal jargon
            </div>
            <div style="color: #64748b; font-size: 0.88rem; line-height: 1.6;">
                Every regulation explained in plain English,
                with concrete next steps for your team.
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""
    <div style="text-align: center; color: #94a3b8; font-size: 0.8rem; padding: 1rem;">
        Built at <strong style="color: #475569;">GenAI Zurich Hackathon 2026</strong> 🇨🇭 ·
        Powered by <strong style="color: #475569;">Apify</strong> ·
        <strong style="color: #475569;">OpenRouter</strong> ·
        <strong style="color: #475569;">Claude</strong>
    </div>
    """, unsafe_allow_html=True)
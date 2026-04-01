import streamlit as st
import asyncio
import sys
import os
from dotenv import load_dotenv
import json
import hashlib
from datetime import datetime
from io import BytesIO

load_dotenv()
if hasattr(st, 'secrets'):
    for key, value in st.secrets.items():
        if key not in os.environ:
            os.environ[key] = str(value)

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
    page_title="Vigil – Regulatory Intelligence",
    page_icon="🛡️",
    layout="wide"
)

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable

from openai import OpenAI
from rag.prompt_templates import get_plain_language_prompt


# ----- CSS CONFIG -----


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

    header[data-testid="stHeader"] {
        display: none !important;
    }

    .stTabs [data-baseweb="tab-list"] {
        background: transparent !important;
        border-bottom: 1px solid #e8edf5 !important;
        gap: 0 !important;
    }

    .stTabs [data-baseweb="tab"] {
        background: transparent !important;
        color: #64748b !important;
        -webkit-text-fill-color: #64748b !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        padding: 0.8rem 1.5rem !important;
        border: none !important;
    }

    .stTabs [aria-selected="true"] {
        color: #2563eb !important;
        -webkit-text-fill-color: #2563eb !important;
        border-bottom: 2px solid #2563eb !important;
        background: transparent !important;
    }

    .stTabs [data-baseweb="tab"] p,
    .stTabs [data-baseweb="tab"] span {
        color: inherit !important;
        -webkit-text-fill-color: inherit !important;
    }

    section[data-testid="stSidebar"] {
        background: #ffffff !important;
        border-right: 1px solid #e8edf5;
    }

    section[data-testid="stSidebar"] * {
        color: #1a1f36 !important;
        -webkit-text-fill-color: #1a1f36 !important;
    }

    section[data-testid="stSidebar"] label {
        color: #374151 !important;
        -webkit-text-fill-color: #374151 !important;
        font-weight: 500 !important;
    }

    section[data-testid="stSidebar"] input,
    section[data-testid="stSidebar"] [data-baseweb="base-input"] {
        background-color: #f8faff !important;
        color: #1a1f36 !important;
        -webkit-text-fill-color: #1a1f36 !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 8px !important;
    }

    section[data-testid="stSidebar"] [data-baseweb="select"] > div {
        background-color: #f8faff !important;
        color: #1a1f36 !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 8px !important;
    }

    section[data-testid="stSidebar"] .stButton > button,
    section[data-testid="stSidebar"] .stButton > button *,
    section[data-testid="stSidebar"] .stButton > button p {
        color: white !important;
        -webkit-text-fill-color: white !important;
    }

    section[data-testid="stSidebar"] [data-testid="stMultiSelect"],
    [data-testid="stMultiSelect"] {
        overflow: visible !important;
    }

    section[data-testid="stSidebar"] [data-baseweb="tag"] {
        max-width: 100% !important;
        overflow: hidden !important;
        white-space: nowrap !important;
        text-overflow: ellipsis !important;
    }

    section[data-testid="stSidebar"] [data-testid="stMultiSelect"] > div::after {
        display: none !important;
    }

    .stButton > button,
    [data-testid="stDownloadButton"] button {
        background: linear-gradient(135deg, #2563eb, #6366f1) !important;
        color: white !important;
        -webkit-text-fill-color: white !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        padding: 0.6rem 1.5rem !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 4px 12px rgba(37,99,235,0.3) !important;
    }

    .stButton > button *,
    .stButton > button p,
    .stButton > button span,
    [data-testid="stDownloadButton"] button *,
    [data-testid="stDownloadButton"] button p {
        color: white !important;
        -webkit-text-fill-color: white !important;
    }

    div[data-testid="stMetricValue"],
    div[data-testid="stMetricValue"] * {
        color: #0f172a !important;
        -webkit-text-fill-color: #0f172a !important;
        font-weight: 700 !important;
    }

    div[data-testid="stMetricLabel"],
    div[data-testid="stMetricLabel"] *,
    div[data-testid="stMetricLabel"] p,
    div[data-testid="stMetricLabel"] span,
    div[data-testid="stMetricLabel"] div {
        color: #0f172a !important;
        -webkit-text-fill-color: #0f172a !important;
        font-weight: 600 !important;
        opacity: 1 !important;
        visibility: visible !important;
    }
            
    [data-testid="stMetricLabel"] > div,
    [data-testid="stMetricLabel"] > div > div,
    [data-testid="stMetricLabel"] label {
        color: #0f172a !important;
        -webkit-text-fill-color: #0f172a !important;
        opacity: 1 !important;
    }

    div[data-testid="stStatusWidget"],
    [data-testid="stStatus"],
    div[data-testid="stStatus"] {
        background: linear-gradient(135deg, #dbeafe, #e0e7ff) !important;
        border: 1px solid #bfdbfe !important;
        border-radius: 12px !important;
    }

    div[data-testid="stStatusWidget"] *,
    [data-testid="stStatus"] *,
    div[data-testid="stStatus"] * {
        color: #1e40af !important;
        -webkit-text-fill-color: #1e40af !important;
    }

    [data-testid="stExpander"] {
        border: 1px solid #e8edf5 !important;
        border-radius: 10px !important;
        background: white !important;
        overflow: visible !important;
    }

    [data-testid="stExpander"] summary {
        background: white !important;
        border-radius: 10px !important;
        padding: 0.8rem 1rem !important;
    }

    [data-testid="stExpander"] summary *,
    [data-testid="stExpander"] summary p {
        color: #1a1f36 !important;
        -webkit-text-fill-color: #1a1f36 !important;
    }

    [data-baseweb="popover"],
    [data-baseweb="menu"] {
        background-color: white !important;
    }

    [data-baseweb="option"] {
        background-color: white !important;
        color: #1a1f36 !important;
    }

    h1, h2, h3 {
        color: #0f172a !important;
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
    }

    .feature-pill {
        display: inline-flex;
        align-items: center;
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

    .reg-card {
        background: white;
        border: 1px solid #e8edf5;
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 4px rgba(0,0,0,0.04);
    }

    .reg-tag {
        display: inline-block;
        background: #eff6ff;
        color: #2563eb;
        font-size: 0.75rem;
        font-weight: 700;
        padding: 0.25rem 0.7rem;
        border-radius: 100px;
        margin-bottom: 0.8rem;
        border: 1px solid #bfdbfe;
    }

    div[data-testid="stAlert"] p,
    div[data-testid="stAlert"] {
        color: #166534 !important;
        -webkit-text-fill-color: #166534 !important;
    }

</style>
""", unsafe_allow_html=True)


# ----- HELPERS -----


CACHE_DIR = "cache"

def _ensure_cache_dir():
    os.makedirs(CACHE_DIR, exist_ok=True)

def _profile_hash(company_profile: dict) -> str:
    key = f"{company_profile['industry']}_{company_profile['country']}_{sorted(company_profile['areas_of_concern'])}"
    return hashlib.md5(key.encode()).hexdigest()[:8]

def _cache_path(company_profile: dict) -> str:
    _ensure_cache_dir()
    return os.path.join(CACHE_DIR, f"cache_{_profile_hash(company_profile)}.json")

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


def _generate_pdf(markdown_text: str, company_name: str) -> bytes:

    try:
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=A4,
            rightMargin=2*cm, leftMargin=2*cm,
            topMargin=2*cm, bottomMargin=2*cm
        )
        styles = getSampleStyleSheet()
        story = []

        title_style = ParagraphStyle('VTitle', parent=styles['Heading1'],
            fontSize=20, textColor=colors.HexColor('#0f172a'),
            spaceAfter=6, fontName='Helvetica-Bold')
        h2_style = ParagraphStyle('VH2', parent=styles['Heading2'],
            fontSize=14, textColor=colors.HexColor('#1e40af'),
            spaceBefore=12, spaceAfter=4, fontName='Helvetica-Bold')
        h3_style = ParagraphStyle('VH3', parent=styles['Heading3'],
            fontSize=11, textColor=colors.HexColor('#374151'),
            spaceBefore=8, spaceAfter=2, fontName='Helvetica-Bold')
        body_style = ParagraphStyle('VBody', parent=styles['Normal'],
            fontSize=10, textColor=colors.HexColor('#374151'),
            spaceAfter=4, leading=15)
        meta_style = ParagraphStyle('VMeta', parent=styles['Normal'],
            fontSize=8, textColor=colors.HexColor('#94a3b8'), spaceAfter=12)

        story.append(Paragraph("Vigil – Regulatory Digest", title_style))
        story.append(Paragraph(
            f"Company: {company_name} · Generated: {datetime.now().strftime('%B %d, %Y')}",
            meta_style))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e8edf5')))
        story.append(Spacer(1, 0.3*cm))

        for line in markdown_text.split('\n'):
            line = line.strip()
            if not line:
                story.append(Spacer(1, 0.2*cm))
            elif line.startswith('# '):
                story.append(Paragraph(line[2:], title_style))
            elif line.startswith('## '):
                story.append(Paragraph(line[3:], h2_style))
            elif line.startswith('### '):
                story.append(Paragraph(line[4:], h3_style))
            elif line.startswith('- ') or line.startswith('* '):
                story.append(Paragraph(f"• {line[2:]}", body_style))
            elif line.startswith('---'):
                story.append(HRFlowable(width="100%", thickness=0.5,
                    color=colors.HexColor('#e8edf5')))
            else:
                clean = line.replace('**', '').replace('*', '').replace('`', '')
                if clean:
                    story.append(Paragraph(clean, body_style))

        doc.build(story)
        return buffer.getvalue()

    except ImportError:

        return markdown_text.encode('utf-8')


async def run_vigil(company_profile: dict) -> dict:

    client = ApifyClient(token=os.getenv("APIFY_TOKEN"))
    test_mode = company_profile.get("test_mode", True)

    with st.status("🔍 Vigil is working...", expanded=True) as status:

        st.write("📡 Scraping regulatory sources...")
        eurlex_docs, gdpr_docs, national_docs = await asyncio.gather(
            scrape_eurlex(client, company_profile, test_mode=test_mode),
            scrape_gdpr(client, company_profile, test_mode=test_mode),
            scrape_national(client, company_profile, test_mode=test_mode)
        )
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
        st.success("✅ No urgent alerts this month – you're compliant!")
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

        source = (summary.get('source') or '').upper()
        title = summary.get('title', f'Update {i}')
    
        if title:
            parts = title.split(' — ') if ' — ' in title else [title]
            unique_parts = list(dict.fromkeys(p.strip() for p in parts))
            title = ' — '.join(unique_parts)

        with st.expander(f"📋 {title}"):
            st.markdown(f'<span class="source-badge">{source}</span>',
                       unsafe_allow_html=True)
            st.markdown(summary.get("plain_summary", ""))
            if summary.get('url'):
                st.caption(f"🔗 [{summary.get('url')}]({summary.get('url')})")


def _get_regulation_explainer(area: str, company_profile: dict) -> str:
    """Generates a personalized regulation explainer using LLM."""

    regulation_context = {
        "GDPR": "General Data Protection Regulation (GDPR) - EU law governing personal data processing. Key rules: legal basis for processing, 72h breach notification, data subject rights, data minimization, fines up to €20M or 4% global turnover.",
        "AI Act": "EU AI Act - world's first comprehensive AI regulation. Risk-based classification: prohibited AI, high-risk AI (conformity assessment required), limited risk, minimal risk. GPAI models have transparency obligations. Phased implementation 2024-2027.",
        "PSD2": "Payment Services Directive 2 - EU payment regulation. Strong Customer Authentication (SCA) mandatory. Open banking: banks must provide API access. Payment service providers need national authorization. Liability rules for unauthorized transactions.",
        "NIS2": "NIS2 Directive - EU cybersecurity law. Mandatory 24h initial + 72h full incident reporting. Supply chain security. Minimum cybersecurity measures. Senior management personal liability. Covers energy, transport, health, finance, digital infrastructure.",
        "DORA": "Digital Operational Resilience Act - EU financial ICT regulation. ICT risk management framework required. Major incident reporting. Regular resilience testing. Oversight of critical third-party ICT providers. Applies to financial entities.",
        "AML": "Anti-Money Laundering Directive - EU AML framework. KYC checks mandatory. Suspicious transaction reporting to FIUs. Enhanced due diligence for high-risk customers. 5-year record keeping. Applies to banks, crypto, lawyers, accountants, real estate.",
    }

    context = regulation_context.get(area, area)

    try:
        client = OpenAI(
            base_url=os.getenv("OPENROUTER_ACTOR_URL", "https://openrouter.apify.actor/api/v1"),
            api_key="no-key-required-but-must-not-be-empty",
            default_headers={
                "Authorization": f"Bearer {os.getenv('APIFY_TOKEN', '')}"
            }
        )

        prompt = get_plain_language_prompt(context, company_profile, mode="explainer")

        response = client.chat.completions.create(
            model="anthropic/claude-3-haiku",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content

    except Exception as e:
        return f"Could not generate personalized explainer: {e}"


def _cache_library_path(company_profile: dict) -> str:
    _ensure_cache_dir()
    key = f"lib_{company_profile['industry']}_{company_profile['country']}"
    h = hashlib.md5(key.encode()).hexdigest()[:8]
    return os.path.join(CACHE_DIR, f"library_{h}.json")

def _load_library_cache(company_profile: dict) -> dict:
    path = _cache_library_path(company_profile)
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {}

def _save_library_cache(company_profile: dict, data: dict):
    path = _cache_library_path(company_profile)
    with open(path, "w") as f:
        json.dump(data, f)


def render_regulation_library(areas: list, company_profile: dict):
    
    regulation_meta = {
        "GDPR":   {"full_name": "General Data Protection Regulation", "emoji": "🔒", "effective": "May 25, 2018",           "link": "https://gdpr.eu"},
        "AI Act": {"full_name": "EU Artificial Intelligence Act",      "emoji": "🤖", "effective": "August 1, 2024",         "link": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32024R1689"},
        "PSD2":   {"full_name": "Payment Services Directive 2",        "emoji": "💳", "effective": "January 13, 2018",       "link": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32015L2366"},
        "NIS2":   {"full_name": "Network and Information Security Dir.","emoji": "🛡️", "effective": "October 17, 2024",      "link": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32022L2555"},
        "DORA":   {"full_name": "Digital Operational Resilience Act",  "emoji": "🏦", "effective": "January 17, 2025",       "link": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32022R2554"},
        "AML":    {"full_name": "Anti-Money Laundering Directive",     "emoji": "🏴‍☠️", "effective": "June 2021 (6th AMLD)", "link": "https://ec.europa.eu/info/law/anti-money-laundering-directive-directive-eu-2018-843_en"},
    }

    st.markdown("### 📚 Regulation library")
    st.caption(f"Personalized for **{company_profile.get('company_name', 'your company')}** · {company_profile.get('industry', '')} · {company_profile.get('country', '')}")

    if not areas:
        st.info("Select regulations in the sidebar to see explainers.")
        return

    library_cache = _load_library_cache(company_profile)

    for area in areas:

        meta = regulation_meta.get(area)
        if not meta:
            continue

        if area not in library_cache:
            with st.spinner(f"Generating personalized explainer for {area}..."):
                library_cache[area] = _get_regulation_explainer(area, company_profile)
                _save_library_cache(company_profile, library_cache)

        explainer = library_cache[area]

        st.markdown(f"""
        <div class="reg-card">
            <div class="reg-tag">{meta['emoji']} {area}</div>
            <div style="font-size: 1.1rem; font-weight: 700; color: #0f172a; margin-bottom: 0.3rem;">
                {meta['full_name']}
            </div>
            <div style="font-size: 0.8rem; color: #94a3b8; margin-bottom: 1rem;">
                In force: {meta['effective']}
            </div>
            <div style="color: #475569; font-size: 0.9rem; line-height: 1.7; margin-bottom: 1rem;">
                {explainer.replace(chr(10), '<br>')}
            </div>
            <div style="margin-top: 1rem;">
                <a href="{meta['link']}" target="_blank"
                   style="color: #2563eb; font-size: 0.85rem; font-weight: 500;">
                    📄 Read the full regulation →
                </a>
            </div>
        </div>
        """, unsafe_allow_html=True)


# ----- SIDEBAR -----


with st.sidebar:

    st.markdown("""
    <div style="padding: 1rem 0 0.5rem 0;">
        <div style="font-size: 1.8rem; font-weight: 800; color: #0f172a; letter-spacing: -0.02em;">
            🛡️ Vigil
        </div>
        <div style="font-size: 0.8rem; color: #94a3b8; font-weight: 500; margin-top: 0.2rem;">
            Regulatory intelligence
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()
    st.markdown("**Company profile**")
    st.caption("Personalize your regulatory feed")

    company_name = st.text_input("Company name", value="TechStartup GmbH")
    industry = st.selectbox("Industry", [
        "fintech", "healthcare", "ecommerce", "saas", "manufacturing"
    ])
    country = st.selectbox("Country", [
        # "DE", "PL", "FR", "CH", "NL", "IT", "ES", "AT", "BE", "SE"
        "DE", "PL", "FR", "CH", "NL", "IT", "ES", "AT", "BE", "SE",
        "IE", "LU", "DK", "FI", "PT", "CZ", "HU", "RO"
    ])
    size = st.selectbox("Company size", ["startup", "sme", "enterprise"])
    areas = st.multiselect(
        "Monitor regulations",
        ["GDPR", "AI Act", "PSD2", "AML", "NIS2", "DORA"],
        default=["GDPR", "AI Act"]
    )
    test_mode = st.toggle("⚡ Fast mode", value=True,
                          help="Uses cached results for instant demo")

    st.divider()
    run_button = st.button("🚀 Generate digest", type="primary",
                           use_container_width=True)

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


# ----- TABS -----


company_profile = {
                "company_name": company_name,
                "industry": industry,
                "country": country,
                "size": size,
                "areas_of_concern": areas,
                "test_mode": test_mode
            }

tab1, tab2, tab3 = st.tabs(["📋 Digest", "📚 Regulation library", "🛡️ /vigil Skill"])

with tab2:
    render_regulation_library(areas, company_profile)

with tab3:
    st.markdown("""
    <div style="max-width:760px;margin:0 auto;">
        <div style="text-align:center;padding:2rem 0 1rem;">
            <div style="font-size:3rem;margin-bottom:0.5rem;">🛡️</div>
            <h2 style="color:#0f172a;margin:0;">The <code>/vigil</code> Skill</h2>
            <p style="color:#64748b;font-size:1.05rem;margin-top:0.5rem;">
                Scan any codebase for EU regulatory compliance issues — directly from your terminal.
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.markdown("""
        <div style="background:white;border:1px solid #e8edf5;border-radius:16px;
                    padding:1.8rem;box-shadow:0 1px 4px rgba(0,0,0,0.04);">
            <h3 style="color:#0f172a;margin-top:0;">What it checks</h3>
            <ul style="color:#475569;line-height:2;font-size:0.92rem;">
                <li>🔐 PII storage without encryption <span style="color:#94a3b8;">(GDPR Art. 32)</span></li>
                <li>📋 Logging personal data <span style="color:#94a3b8;">(GDPR Art. 5)</span></li>
                <li>🌍 Cross-border data transfers <span style="color:#94a3b8;">(GDPR Art. 46)</span></li>
                <li>🤖 Automated decisions without human review <span style="color:#94a3b8;">(AI Act Art. 14)</span></li>
                <li>📝 Missing consent mechanisms <span style="color:#94a3b8;">(GDPR Art. 7)</span></li>
                <li>🗑️ No data retention / deletion policy <span style="color:#94a3b8;">(GDPR Art. 17)</span></li>
                <li>🔑 Hardcoded credentials <span style="color:#94a3b8;">(Security best practice)</span></li>
                <li>🧠 AI without transparency disclosures <span style="color:#94a3b8;">(AI Act Art. 52)</span></li>
                <li>📄 Privacy policy gaps <span style="color:#94a3b8;">(GDPR Art. 13/14)</span></li>
                <li>☁️ Non-EU cloud infrastructure <span style="color:#94a3b8;">(GDPR Art. 46)</span></li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    with col_right:
        st.markdown("""
        <div style="background:white;border:1px solid #e8edf5;border-radius:16px;
                    padding:1.8rem;box-shadow:0 1px 4px rgba(0,0,0,0.04);">
            <h3 style="color:#0f172a;margin-top:0;">What you need</h3>
            <ul style="color:#475569;line-height:2.2;font-size:0.92rem;padding-left:1.2rem;">
                <li><strong>Node.js</strong> (v18+) — <a href="https://nodejs.org" target="_blank">nodejs.org</a></li>
                <li><strong>Claude Code</strong> — Anthropic's CLI agent</li>
                <li><strong>Anthropic API key</strong> — <a href="https://console.anthropic.com" target="_blank">console.anthropic.com</a></li>
            </ul>
            <div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:10px;padding:1rem;margin-top:1rem;">
                <p style="color:#1e40af;font-size:0.85rem;margin:0;">
                    💡 <strong>No coding required.</strong> You just type one command and Vigil scans your whole project automatically.
                </p>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Download button
    skill_path = os.path.join(os.path.dirname(__file__), "skill", "vigil-compliance.md")
    try:
        with open(skill_path, "r", encoding="utf-8") as f:
            skill_content = f.read()
    except FileNotFoundError:
        skill_content = "# Skill file not found\nPlease check the repository."

    col_dl1, col_dl2, col_dl3 = st.columns([1, 2, 1])
    with col_dl2:
        st.download_button(
            label="⬇️  Download SKILL.md",
            data=skill_content,
            file_name="SKILL.md",
            mime="text/markdown",
            use_container_width=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Step-by-step instructions with OS tabs
    st.markdown("### Step-by-step setup")
    os_tab_win, os_tab_mac = st.tabs(["🪟 Windows", "🍎 Mac / Linux"])

    with os_tab_win:
        st.markdown("""
#### Step 1 — Install Claude Code

Open **PowerShell** (search "PowerShell" in Start menu) and paste:

```
npm install -g @anthropic-ai/claude-code
```

> Don't have `npm`? Install Node.js first from [nodejs.org](https://nodejs.org) (download the LTS version, run the installer, restart PowerShell).

---

#### Step 2 — Install the /vigil skill

Still in PowerShell, paste these **3 lines one by one**:

```
mkdir "$env:USERPROFILE\\.claude\\skills\\vigil" -Force
```

```
Copy-Item "$env:USERPROFILE\\Downloads\\SKILL.md" "$env:USERPROFILE\\.claude\\skills\\vigil\\SKILL.md"
```

> This assumes you downloaded `SKILL.md` to your Downloads folder using the button above.
> If you saved it elsewhere, replace `Downloads\\SKILL.md` with the correct path.

To verify it worked:

```
cat "$env:USERPROFILE\\.claude\\skills\\vigil\\SKILL.md"
```

You should see the skill file contents.

---

#### Step 3 — Go to your project folder

```
cd C:\\path\\to\\your-project
```

For example:
```
cd C:\\Users\\YourName\\Documents\\my-app
```

---

#### Step 4 — Run the scan

Start Claude Code:
```
claude
```

Wait for it to load, then type:
```
/vigil
```

That's it! Vigil will scan your entire project and generate a compliance report with specific findings, file paths, and recommended fixes.
        """)

    with os_tab_mac:
        st.markdown("""
#### Step 1 — Install Claude Code

Open **Terminal** (Cmd+Space, type "Terminal") and paste:

```bash
npm install -g @anthropic-ai/claude-code
```

> Don't have `npm`? Install Node.js first: `brew install node` (if you have Homebrew) or download from [nodejs.org](https://nodejs.org).

---

#### Step 2 — Install the /vigil skill

Still in Terminal, paste these **2 lines one by one**:

```bash
mkdir -p ~/.claude/skills/vigil
```

```bash
cp ~/Downloads/SKILL.md ~/.claude/skills/vigil/SKILL.md
```

> This assumes you downloaded `SKILL.md` to your Downloads folder using the button above.
> If you saved it elsewhere, replace `~/Downloads/SKILL.md` with the correct path.

To verify it worked:

```bash
cat ~/.claude/skills/vigil/SKILL.md
```

You should see the skill file contents.

---

#### Step 3 — Go to your project folder

```bash
cd /path/to/your-project
```

For example:
```bash
cd ~/Documents/my-app
```

---

#### Step 4 — Run the scan

Start Claude Code:
```bash
claude
```

Wait for it to load, then type:
```
/vigil
```

That's it! Vigil will scan your entire project and generate a compliance report with specific findings, file paths, and recommended fixes.
        """)

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Example output
    with st.expander("📋 Example: what /vigil finds in a fintech app", expanded=False):
        st.markdown("""
**Repository:** sample-fintech-app
**Scanned:** 4 source files, 1 document, 1 config
**Issues found:** 8

---

### 🔴 Critical (immediate legal risk)

**PII logged in plaintext**
- File: `app.py:15`
- Regulation: GDPR Article 5(1)(f)
- Issue: User email addresses are printed to stdout in plaintext during login
- Fix: Remove PII from logs or use pseudonymization

**Automated credit scoring without human oversight**
- File: `scoring.py:10`
- Regulation: AI Act Article 14, GDPR Article 22
- Issue: Credit decisions are fully automated with no human-in-the-loop or appeal mechanism
- Fix: Add human review step for denied applications, implement right to explanation

**Hardcoded database credentials**
- File: `config.py:6`
- Regulation: Security best practice (NIS2 Art. 21)
- Issue: Production database password stored in source code
- Fix: Use environment variables or a secrets manager

---

### 🟠 High (significant compliance gap)

**Non-EU data storage**
- File: `config.py:9`
- Regulation: GDPR Article 46
- Issue: AWS region set to `us-east-1` — personal data stored outside EU
- Fix: Migrate to `eu-central-1` or implement Standard Contractual Clauses

**No transparency disclosure for AI decisions**
- File: `scoring.py:19`
- Regulation: AI Act Article 52
- Issue: Users are not informed that decisions are made by AI
- Fix: Add clear disclosure that credit scoring uses automated AI processing
        """)

    st.markdown("""
    <div style="text-align:center;color:#94a3b8;font-size:0.8rem;padding:1rem;">
        The /vigil skill is open source · Works with any codebase · Powered by <strong style="color:#475569;">Claude</strong>
    </div>
    """, unsafe_allow_html=True)

with tab1:
    if run_button:
        if not areas:
            st.warning("Please select at least one regulatory area.")
        else:
            cached = _load_cache(company_profile)
            if cached and test_mode:
                st.info("⚡ Loaded from cache – instant results!")
                output = cached
            else:
                output = asyncio.run(run_vigil(company_profile))
                _save_cache(company_profile, output)

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("📚 Sources analyzed", output.get("sources_analyzed", 0))
            with col2:
                st.metric("🚨 Total alerts", output.get("alerts_count", 0))
            with col3:
                st.metric("🔴 Critical", len(output.get("critical_alerts", [])))
            with col4:
                st.metric("🟠 High priority", len(output.get("high_alerts", [])))

            st.divider()
            col_left, col_right = st.columns([3, 2])

            with col_left:
                st.markdown('<div class="digest-container">', unsafe_allow_html=True)
                st.subheader("📋 Monthly digest")
                st.markdown(output.get("digest_markdown", ""))
                st.markdown('</div>', unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)
                st.subheader("🗣️ What changed – plain language")
                st.caption("Key regulatory updates explained for your business, no jargon.")
                render_plain_summaries(output)

            with col_right:
                try:
                    st.subheader("🚨 Alerts")
                    render_alerts(output)

                    st.divider()
                    st.subheader("📥 Download report")
                    md_data = output.get("full_report_markdown", "")
                    pdf_data = _generate_pdf(md_data, company_name)

                    col_dl1, col_dl2 = st.columns(2)
                    with col_dl1:
                        st.download_button(
                            label="⬇️ PDF",
                            data=pdf_data,
                            file_name=f"vigil_{company_name.replace(' ', '_')}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                    with col_dl2:
                        st.download_button(
                            label="⬇️ Markdown",
                            data=md_data,
                            file_name=f"vigil_{company_name.replace(' ', '_')}.md",
                            mime="text/markdown",
                            use_container_width=True
                        )
                except Exception as e:
                    st.error(f"Error rendering right column: {e}")

    else:
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
                    personalized, actionable compliance alerts –
                    <strong>before the deadline hits.</strong>
                </div>
                <div>
                    <span class="feature-pill">📋 Monthly digests</span>
                    <span class="feature-pill">🚨 Deadline alerts</span>
                    <span class="feature-pill">🗣️ Plain language</span>
                    <span class="feature-pill">💡 Strategic insights</span>
                    <span class="feature-pill">📥 PDF reports</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("""
            <div style="background:white;border:1px solid #e8edf5;border-radius:16px;
                        padding:1.5rem;box-shadow:0 1px 4px rgba(0,0,0,0.04);">
                <div style="font-size:2rem;margin-bottom:0.8rem;">⚡</div>
                <div style="font-weight:700;color:#0f172a;margin-bottom:0.5rem;">Real-time monitoring</div>
                <div style="color:#64748b;font-size:0.88rem;line-height:1.6;">
                    Vigil scrapes EUR-Lex, EDPB, and national regulators – so you never miss a change.
                </div>
            </div>""", unsafe_allow_html=True)
        with col2:
            st.markdown("""
            <div style="background:white;border:1px solid #e8edf5;border-radius:16px;
                        padding:1.5rem;box-shadow:0 1px 4px rgba(0,0,0,0.04);">
                <div style="font-size:2rem;margin-bottom:0.8rem;">🎯</div>
                <div style="font-weight:700;color:#0f172a;margin-bottom:0.5rem;">Personalized to your business</div>
                <div style="color:#64748b;font-size:0.88rem;line-height:1.6;">
                    Enter your industry, country, and regulatory areas. Vigil filters everything irrelevant.
                </div>
            </div>""", unsafe_allow_html=True)
        with col3:
            st.markdown("""
            <div style="background:white;border:1px solid #e8edf5;border-radius:16px;
                        padding:1.5rem;box-shadow:0 1px 4px rgba(0,0,0,0.04);">
                <div style="font-size:2rem;margin-bottom:0.8rem;">🗣️</div>
                <div style="font-weight:700;color:#0f172a;margin-bottom:0.5rem;">No legal jargon</div>
                <div style="color:#64748b;font-size:0.88rem;line-height:1.6;">
                    Every regulation explained in plain English, with concrete next steps.
                </div>
            </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""
        <div style="text-align:center;color:#94a3b8;font-size:0.8rem;padding:1rem;">
            Built at <strong style="color:#475569;">GenAI Zurich Hackathon 2026</strong> 🇨🇭 ·
            Powered by <strong style="color:#475569;">Apify</strong> ·
            <strong style="color:#475569;">OpenRouter</strong> ·
            <strong style="color:#475569;">Claude</strong>
        </div>
        """, unsafe_allow_html=True)
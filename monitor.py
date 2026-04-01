"""
Vigil Pipeline Monitor — business-friendly view of what Vigil is doing.
Separate from the main dashboard. Shows judges the system works live.

Usage:
    streamlit run monitor.py --server.port 8502
"""

import streamlit as st
from streamlit_autorefresh import st_autorefresh
import sqlite3
import json
import os
from datetime import datetime

st.set_page_config(
    page_title="Vigil — Pipeline Monitor",
    page_icon="⚡",
    layout="wide",
)

# Auto-refresh every 5 seconds
st_autorefresh(interval=5000, key="monitor_refresh")

# ── CSS ──────────────────────────────────────────────────────────────────

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background: #0a1628; color: #f0f4ff; }
    header[data-testid="stHeader"] { display: none !important; }
    section[data-testid="stSidebar"] { display: none !important; }

    .step-box {
        background: #0f2140;
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        margin-bottom: 0.8rem;
    }
    .step-box.active {
        border-color: #22d3ee;
        box-shadow: 0 0 20px rgba(34, 211, 238, 0.1);
    }
    .step-box.done {
        border-color: #22c55e;
    }

    .step-header {
        display: flex;
        align-items: center;
        gap: 0.8rem;
        margin-bottom: 0.4rem;
    }
    .step-icon {
        width: 32px;
        height: 32px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.85rem;
        font-weight: 700;
    }
    .step-icon.find { background: rgba(34, 211, 238, 0.15); color: #22d3ee; }
    .step-icon.warn { background: rgba(245, 158, 11, 0.15); color: #f59e0b; }
    .step-icon.report { background: rgba(239, 68, 68, 0.15); color: #ef4444; }
    .step-icon.protect { background: rgba(34, 197, 94, 0.15); color: #22c55e; }

    .step-title {
        font-weight: 700;
        font-size: 1rem;
    }
    .step-detail {
        color: #94a3b8;
        font-size: 0.85rem;
        margin-left: 2.8rem;
    }
    .step-metric {
        display: inline-block;
        background: rgba(255,255,255,0.05);
        padding: 0.2rem 0.7rem;
        border-radius: 6px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-right: 0.5rem;
        margin-top: 0.3rem;
    }

    .log-entry {
        font-family: 'JetBrains Mono', 'Fira Code', monospace;
        font-size: 0.78rem;
        line-height: 1.8;
        color: #64748b;
        padding: 0.3rem 0;
        border-bottom: 1px solid rgba(255,255,255,0.03);
    }
    .log-entry .time { color: #475569; }
    .log-entry .ok { color: #22c55e; }
    .log-entry .info { color: #22d3ee; }
    .log-entry .warn { color: #f59e0b; }
</style>
""", unsafe_allow_html=True)


# ── Header ───────────────────────────────────────────────────────────────

st.markdown("""
<div style="text-align:center; padding: 1.5rem 0 1rem;">
    <h1 style="color:#22d3ee; font-size:1.8rem; margin:0; letter-spacing:0.05em;">
        VIGIL <span style="color:#94a3b8; font-weight:400;">Pipeline Monitor</span>
    </h1>
    <p style="color:#64748b; font-size:0.9rem; margin-top:0.3rem;">
        Real-time view of the Find &rarr; Warn &rarr; Report &rarr; Protect pipeline
    </p>
</div>
""", unsafe_allow_html=True)


# ── Load data from SQLite ────────────────────────────────────────────────

DB_PATH = "vigil.db"

def get_outreach_log():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT o.*, c.name, c.industry, c.country FROM outreach_log o "
            "LEFT JOIN companies c ON o.company_id = c.id "
            "ORDER BY o.attempted_at DESC LIMIT 20"
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []

def get_companies():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM companies ORDER BY discovered_at DESC").fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []

def get_call_scripts():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT cs.*, c.name FROM call_scripts cs "
            "LEFT JOIN companies c ON cs.company_id = c.id "
            "ORDER BY cs.created_at DESC LIMIT 5"
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []

# Load data
logs = get_outreach_log()
companies = get_companies()
scripts = get_call_scripts()

# Load facts if available
facts_path = os.path.join("demo", "pre_scraped_facts.json")
facts = []
try:
    with open(facts_path) as f:
        facts = json.load(f)
except Exception:
    pass

# Load alert
alert_path = os.path.join("demo", "mock_alert.json")
alert = {}
try:
    with open(alert_path) as f:
        alert = json.load(f)
except Exception:
    pass

# Count stats
total_calls = len([l for l in logs if l.get("channel") == "voice"])
total_emails = len([l for l in logs if l.get("channel") == "email"])
completed_calls = len([l for l in logs if l.get("status") == "completed"])
reg_facts = [f for f in facts if f.get("regulation")]


st.markdown("<br>", unsafe_allow_html=True)


# ── Pipeline steps ───────────────────────────────────────────────────────

col_pipeline, col_log = st.columns([3, 2])

with col_pipeline:
    st.markdown("### Pipeline Activity")

    # FIND — Regulations
    has_facts = len(reg_facts) > 0
    st.markdown(f"""
    <div class="step-box {'done' if has_facts else ''}">
        <div class="step-header">
            <div class="step-icon find">{'✓' if has_facts else '1'}</div>
            <div class="step-title" style="color:#22d3ee;">FIND — Regulatory Sources</div>
        </div>
        <div class="step-detail">
            {'Scraped EUR-Lex, EDPB, and national regulators via Apify' if has_facts else 'Waiting for pipeline run...'}
            <br>
            <span class="step-metric" style="color:#22d3ee;">{len(reg_facts)} regulatory facts</span>
            <span class="step-metric" style="color:#22d3ee;">3 regulations (GDPR, AI Act, PSD2)</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # FIND — Registries
    has_companies = len(companies) > 0
    st.markdown(f"""
    <div class="step-box {'done' if has_companies else ''}">
        <div class="step-header">
            <div class="step-icon find">{'✓' if has_companies else '1'}</div>
            <div class="step-title" style="color:#22d3ee;">FIND — Business Registries</div>
        </div>
        <div class="step-detail">
            {'Scraped business registries and identified companies at risk' if has_companies else 'Waiting for pipeline run...'}
            <br>
            {''.join(f'<span class="step-metric" style="color:#22d3ee;">{c["name"]} ({c.get("industry", "?")})</span>' for c in companies[:3])}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # MATCH
    has_alert = bool(alert)
    severity = alert.get("severity", "high").upper() if alert else ""
    sev_color = "#ef4444" if severity == "CRITICAL" else "#f59e0b" if severity == "HIGH" else "#ca8a04"
    st.markdown(f"""
    <div class="step-box {'done' if has_alert else ''}">
        <div class="step-header">
            <div class="step-icon warn">{'✓' if has_alert else '2'}</div>
            <div class="step-title" style="color:#f59e0b;">MATCH — Risk Analysis</div>
        </div>
        <div class="step-detail">
            {'Claude matched companies to regulatory risks' if has_alert else 'Waiting for facts...'}
            <br>
            {f'<span class="step-metric" style="color:{sev_color};">[{severity}] {alert.get("regulation", "")} {alert.get("article", "")}</span>' if has_alert else ''}
            {f'<span class="step-metric" style="color:{sev_color};">{alert.get("days_remaining", "?")} days remaining</span>' if has_alert else ''}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # WARN
    has_calls = total_calls > 0
    st.markdown(f"""
    <div class="step-box {'done' if has_calls else ''}">
        <div class="step-header">
            <div class="step-icon warn">{'✓' if has_calls else '3'}</div>
            <div class="step-title" style="color:#f59e0b;">WARN — Automated Outreach</div>
        </div>
        <div class="step-detail">
            {'Automated compliance alerts delivered' if has_calls else 'Waiting for risk match...'}
            <br>
            <span class="step-metric" style="color:#f59e0b;">{total_calls} call{'s' if total_calls != 1 else ''} placed</span>
            <span class="step-metric" style="color:#ef4444;">{total_emails} report{'s' if total_emails != 1 else ''} sent</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # REPORT
    st.markdown(f"""
    <div class="step-box {'done' if total_emails > 0 else ''}">
        <div class="step-header">
            <div class="step-icon report">{'✓' if total_emails > 0 else '4'}</div>
            <div class="step-title" style="color:#ef4444;">REPORT — Compliance Reports</div>
        </div>
        <div class="step-detail">
            {'Claude-generated compliance reports with legal citations, auditor warnings, and action steps' if total_emails > 0 else 'Reports generated when recipient presses 1 during call'}
            <br>
            <span class="step-metric" style="color:#ef4444;">{total_emails} report{'s' if total_emails != 1 else ''} delivered</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # PROTECT
    st.markdown(f"""
    <div class="step-box">
        <div class="step-header">
            <div class="step-icon protect">5</div>
            <div class="step-title" style="color:#22c55e;">PROTECT — Code Scanning</div>
        </div>
        <div class="step-detail">
            Engineers type <code>/vigil</code> in Claude Code to scan their codebase for compliance issues.
            <br>
            <span class="step-metric" style="color:#22c55e;">10 risk categories</span>
            <span class="step-metric" style="color:#22c55e;">GDPR, AI Act, NIS2, DORA, PSD2</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ── Activity log ─────────────────────────────────────────────────────────

with col_log:
    st.markdown("### Scraping Regulatory Sources & Business Registries")

    # Read live pipeline logs from SQLite
    def get_pipeline_logs():
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM pipeline_log ORDER BY id DESC LIMIT 50"
            ).fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception:
            return []

    pipeline_logs = get_pipeline_logs()

    # Icon mapping for tags
    tag_icons = {
        "PIPELINE": "🚀", "SCRAPE": "🌐", "EXTRACT": "📄", "FACT": "🧠",
        "REGISTRY": "🏢", "MATCH": "🔍", "RISK": "⚠️", "SCRIPT": "📝",
        "CALL": "📞", "REPORT": "📧",
    }

    # Render in scrollable container
    if pipeline_logs:
        log_html = ""
        for entry in pipeline_logs:
            tag = entry.get("tag", "LOG")
            message = entry.get("message", "")
            color = entry.get("color", "info")
            time_str = entry.get("created_at", "")[:19]
            icon = tag_icons.get(tag, "📋")

            log_html += (
                f'<div class="log-entry">'
                f'<span class="time">{time_str}</span> {icon} '
                f'<span class="{color}" style="font-weight:600;">[{tag}]</span> {message}'
                f'</div>'
            )

        container_html = (
            '<div style="max-height:480px;overflow-y:auto;padding:1rem;'
            'border:1px solid rgba(255,255,255,0.04);border-radius:10px;'
            f'background:rgba(0,0,0,0.15);">{log_html}</div>'
        )
        st.markdown(container_html, unsafe_allow_html=True)
    else:
        st.markdown(
            '<div style="color:#64748b;text-align:center;padding:2rem;">'
            'No activity yet. Run the orchestrator to see live updates.<br>'
            '<code style="color:#22d3ee;">python src/outreach/orchestrator.py</code>'
            '</div>',
            unsafe_allow_html=True,
        )

    # Latest call script
    if scripts:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### Latest Call Script")
        latest = scripts[0]
        st.markdown(f"""
        <div style="background:#0f2140; border:1px solid rgba(245,158,11,0.2);
                    border-radius:10px; padding:1.2rem; font-size:0.85rem;
                    color:#f59e0b; line-height:1.7; font-style:italic;">
            "{latest.get('script', 'No script available')}"
        </div>
        <p style="color:#64748b; font-size:0.75rem; margin-top:0.5rem;">
            Generated for {latest.get('name', '?')} at {(latest.get('created_at', ''))[:19]}
        </p>
        """, unsafe_allow_html=True)


# ── Footer ───────────────────────────────────────────────────────────────

st.markdown("""
<div style="text-align:center; color:#475569; font-size:0.75rem; padding:2rem; margin-top:2rem;
            border-top:1px solid rgba(255,255,255,0.04);">
    Vigil Pipeline Monitor — real-time system activity<br>
    Auto-refreshes with each page load · <a href="" target="_self" style="color:#22d3ee;">Refresh now</a>
</div>
""", unsafe_allow_html=True)

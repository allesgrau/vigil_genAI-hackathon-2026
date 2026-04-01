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

    .log-entry {
        font-family: 'JetBrains Mono', 'Fira Code', monospace;
        font-size: 0.82rem;
        line-height: 1.9;
        color: #94a3b8;
        padding: 0.35rem 0.5rem;
        border-bottom: 1px solid rgba(255,255,255,0.03);
    }
    .log-entry .time { color: #475569; font-size: 0.75rem; }
    .log-entry .ok { color: #22c55e; }
    .log-entry .info { color: #22d3ee; }
    .log-entry .warn { color: #f59e0b; }

    .pipeline-bar {
        display: flex;
        gap: 0;
        margin-bottom: 1.5rem;
    }
    .pipeline-step {
        flex: 1;
        padding: 0.8rem 1rem;
        text-align: center;
        font-size: 0.82rem;
        font-weight: 600;
        border-bottom: 3px solid rgba(255,255,255,0.06);
        color: #475569;
        transition: all 0.3s;
    }
    .pipeline-step.done {
        color: #22c55e;
        border-bottom-color: #22c55e;
    }
    .pipeline-step.active {
        color: #22d3ee;
        border-bottom-color: #22d3ee;
    }
    .pipeline-step.waiting {
        color: #475569;
        border-bottom-color: rgba(255,255,255,0.06);
    }
    .pipeline-step .step-label {
        display: block;
        font-size: 0.7rem;
        font-weight: 400;
        margin-top: 0.2rem;
        opacity: 0.7;
    }
</style>
""", unsafe_allow_html=True)


# ── Header ───────────────────────────────────────────────────────────────

st.markdown("""
<div style="text-align:center; padding: 1.5rem 0 0.5rem;">
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

pipeline_logs = get_pipeline_logs()
scripts = get_call_scripts()

# Determine pipeline status from LATEST run only
# Find the most recent "PIPELINE started" entry and only count tags after it
latest_start_id = 0
for entry in pipeline_logs:
    if entry.get("tag") == "PIPELINE" and "started" in entry.get("message", "").lower():
        latest_start_id = entry.get("id", 0)
        break

recent_logs = [e for e in pipeline_logs if e.get("id", 0) >= latest_start_id] if latest_start_id else []
recent_tags = set(e.get("tag", "") for e in recent_logs)
has_scrape = "SCRAPE" in recent_tags
has_extract = "EXTRACT" in recent_tags or "FACT" in recent_tags
has_registry = "REGISTRY" in recent_tags
has_match = "RISK" in recent_tags or "MATCH" in recent_tags
has_call = "CALL" in recent_tags
has_report = any(e.get("tag") == "PIPELINE" and "complete" in e.get("message", "").lower() for e in recent_logs)


# ── Pipeline status bar ─────────────────────────────────────────────────

def step_class(done):
    return "done" if done else "waiting"

st.markdown(f"""
<div class="pipeline-bar">
    <div class="pipeline-step {step_class(has_scrape)}">
        {"✓" if has_scrape else "1"} FIND
        <span class="step-label">Scrape sources</span>
    </div>
    <div class="pipeline-step {step_class(has_registry)}">
        {"✓" if has_registry else "2"} DISCOVER
        <span class="step-label">Business registries</span>
    </div>
    <div class="pipeline-step {step_class(has_match)}">
        {"✓" if has_match else "3"} MATCH
        <span class="step-label">Risk analysis</span>
    </div>
    <div class="pipeline-step {step_class(has_call)}">
        {"✓" if has_call else "4"} WARN
        <span class="step-label">Compliance call</span>
    </div>
    <div class="pipeline-step {step_class(has_report)}">
        {"✓" if has_report else "5"} REPORT
        <span class="step-label">Email report</span>
    </div>
</div>
""", unsafe_allow_html=True)


# ── Main content: Logs (wide) + Call Script (side) ──────────────────────

col_log, col_script = st.columns([3, 1])

with col_log:
    st.markdown("### Live Pipeline Log")

    tag_icons = {
        "PIPELINE": "🚀", "SCRAPE": "🌐", "EXTRACT": "📄", "FACT": "🧠",
        "REGISTRY": "🏢", "MATCH": "🔍", "RISK": "⚠️", "SCRIPT": "📝",
        "CALL": "📞", "REPORT": "📧",
    }

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
            '<div style="max-height:600px;overflow-y:auto;padding:1rem 1.2rem;'
            'border:1px solid rgba(255,255,255,0.04);border-radius:12px;'
            f'background:rgba(0,0,0,0.2);">{log_html}</div>'
        )
        st.markdown(container_html, unsafe_allow_html=True)
    else:
        st.markdown(
            '<div style="color:#475569;text-align:center;padding:4rem 2rem;'
            'border:1px solid rgba(255,255,255,0.04);border-radius:12px;'
            'background:rgba(0,0,0,0.2);font-size:0.95rem;">'
            '⏳ Waiting for pipeline...<br><br>'
            '<span style="color:#64748b;font-size:0.82rem;">'
            'Run <code style="color:#22d3ee;">python src/outreach/orchestrator.py</code> '
            'to see live activity</span>'
            '</div>',
            unsafe_allow_html=True,
        )

with col_script:
    st.markdown("### Latest Call Script")
    if scripts:
        latest = scripts[0]
        script_html = (
            f'<div style="background:#0f2140;border:1px solid rgba(245,158,11,0.2);'
            f'border-radius:12px;padding:1.2rem;font-size:0.88rem;'
            f'color:#f59e0b;line-height:1.8;font-style:italic;">'
            f'"{latest.get("script", "No script available")}"'
            f'</div>'
            f'<p style="color:#64748b;font-size:0.72rem;margin-top:0.5rem;">'
            f'Generated for {latest.get("name", "?")} at {(latest.get("created_at", ""))[:19]}'
            f'</p>'
        )
        st.markdown(script_html, unsafe_allow_html=True)
    else:
        st.markdown(
            '<div style="color:#475569;text-align:center;padding:2rem;'
            'border:1px solid rgba(255,255,255,0.04);border-radius:12px;'
            'background:rgba(0,0,0,0.2);font-size:0.85rem;">'
            '📝 Call script will appear here when generated'
            '</div>',
            unsafe_allow_html=True,
        )


# ── Footer ───────────────────────────────────────────────────────────────

st.markdown("""
<div style="text-align:center; color:#475569; font-size:0.75rem; padding:2rem; margin-top:1rem;
            border-top:1px solid rgba(255,255,255,0.04);">
    Vigil Pipeline Monitor &middot; auto-refreshes every 5 seconds &middot;
    <a href="" target="_self" style="color:#22d3ee;">Refresh now</a>
</div>
""", unsafe_allow_html=True)

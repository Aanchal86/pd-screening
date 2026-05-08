import streamlit as st
import requests
import pandas as pd
import io

BASE_URL = "http://localhost:8000"

# ── Page config ───────────────────────────────────────────
st.set_page_config(
    page_title="NeuroScreen — PD Screening",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Session state init ────────────────────────────────────
for key, default in [
    ("token", None), ("username", None), ("page", "login"),
    ("scores", {"speech": None, "hw": None, "eeg": None}),
    ("patient_name", ""), ("patient_id", None),
    ("last_result", None), ("history_cache", None),
]:
    if key not in st.session_state:
        st.session_state[key] = default

def auth_header():
    return {"Authorization": f"Bearer {st.session_state.token}"}

def go(page):
    st.session_state.page = page
    st.rerun()

# ── Global CSS ────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');

/* ── Reset & base ── */
*, *::before, *::after { box-sizing: border-box; }

html, body, [data-testid="stApp"] {
    font-family: 'DM Sans', sans-serif;
    background: #F4F7FB;
    color: #1A2340;
}

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stToolbar"] { display: none; }
.block-container { padding-top: 1.5rem !important; padding-bottom: 2rem !important; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #0B1E3D !important;
    border-right: 1px solid #1E3A6E;
}
[data-testid="stSidebar"] * { color: #CBD5E8 !important; }
[data-testid="stSidebarContent"] { padding: 0 !important; }

/* ── Cards ── */
.ns-card {
    background: #FFFFFF;
    border-radius: 16px;
    border: 1px solid #E2E8F4;
    padding: 1.75rem;
    box-shadow: 0 2px 12px rgba(11,30,61,0.06);
    margin-bottom: 1rem;
    transition: box-shadow 0.2s;
}
.ns-card:hover { box-shadow: 0 4px 24px rgba(11,30,61,0.1); }

/* ── Stat cards ── */
.stat-card {
    background: #FFFFFF;
    border-radius: 14px;
    border: 1px solid #E2E8F4;
    padding: 1.25rem 1.5rem;
    text-align: center;
    box-shadow: 0 2px 8px rgba(11,30,61,0.05);
}
.stat-num {
    font-size: 2rem;
    font-weight: 700;
    color: #1151A6;
    line-height: 1;
    margin-bottom: 0.25rem;
}
.stat-label {
    font-size: 0.78rem;
    font-weight: 500;
    color: #6B7A99;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}

/* ── Modality cards (home) ── */
.modality-card {
    background: #FFFFFF;
    border-radius: 16px;
    border: 2px solid #E2E8F4;
    padding: 2rem 1.5rem;
    text-align: center;
    cursor: pointer;
    transition: all 0.2s ease;
    position: relative;
    overflow: hidden;
}
.modality-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 4px;
    background: linear-gradient(90deg, #1151A6, #3B82F6);
    opacity: 0;
    transition: opacity 0.2s;
}
.modality-card:hover { border-color: #1151A6; transform: translateY(-2px); box-shadow: 0 8px 24px rgba(17,81,166,0.12); }
.modality-card:hover::before { opacity: 1; }
.modality-icon { font-size: 2.5rem; margin-bottom: 0.75rem; }
.modality-title { font-size: 1.05rem; font-weight: 600; color: #1A2340; margin-bottom: 0.4rem; }
.modality-desc { font-size: 0.82rem; color: #6B7A99; line-height: 1.5; }
.modality-badge {
    display: inline-block;
    margin-top: 0.75rem;
    padding: 0.2rem 0.65rem;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.04em;
}
.badge-done { background: #D1FAE5; color: #065F46; }
.badge-pending { background: #FEF3C7; color: #92400E; }

/* ── Risk badges ── */
.risk-high { background: #FEE2E2; color: #991B1B; border: 1px solid #FECACA; border-radius: 8px; padding: 0.75rem 1rem; font-weight: 600; }
.risk-moderate { background: #FEF3C7; color: #92400E; border: 1px solid #FDE68A; border-radius: 8px; padding: 0.75rem 1rem; font-weight: 600; }
.risk-low { background: #D1FAE5; color: #065F46; border: 1px solid #A7F3D0; border-radius: 8px; padding: 0.75rem 1rem; font-weight: 600; }

/* ── Score pill ── */
.score-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    background: #EFF6FF;
    border: 1px solid #BFDBFE;
    border-radius: 999px;
    padding: 0.35rem 0.9rem;
    font-size: 0.82rem;
    font-weight: 500;
    color: #1D4ED8;
    font-family: 'DM Mono', monospace;
}

/* ── Page header ── */
.page-header {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin-bottom: 1.75rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid #E2E8F4;
}
.page-header-icon {
    width: 44px; height: 44px;
    background: #EFF6FF;
    border-radius: 12px;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.4rem;
    border: 1px solid #BFDBFE;
}
.page-header h1 {
    font-size: 1.5rem !important;
    font-weight: 700 !important;
    color: #1A2340 !important;
    margin: 0 !important;
    padding: 0 !important;
}
.page-header p {
    font-size: 0.85rem;
    color: #6B7A99;
    margin: 0.15rem 0 0 0;
}

/* ── Topbar ── */
.topbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: #FFFFFF;
    border-radius: 14px;
    border: 1px solid #E2E8F4;
    padding: 0.75rem 1.5rem;
    margin-bottom: 1.5rem;
    box-shadow: 0 1px 6px rgba(11,30,61,0.05);
}
.topbar-left { display: flex; align-items: center; gap: 0.75rem; }
.topbar-breadcrumb { font-size: 0.8rem; color: #6B7A99; }
.topbar-page { font-size: 0.95rem; font-weight: 600; color: #1A2340; }
.user-chip {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    background: #F1F5FD;
    border: 1px solid #DBEAFE;
    border-radius: 999px;
    padding: 0.35rem 0.9rem 0.35rem 0.35rem;
}
.user-avatar {
    width: 30px; height: 30px;
    background: linear-gradient(135deg, #1151A6, #3B82F6);
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.75rem;
    font-weight: 700;
    color: white;
}
.user-name { font-size: 0.82rem; font-weight: 600; color: #1A2340; }

/* ── Progress tracker ── */
.progress-tracker {
    display: flex;
    align-items: center;
    background: #FFFFFF;
    border-radius: 14px;
    border: 1px solid #E2E8F4;
    padding: 1rem 1.5rem;
    margin-bottom: 1.5rem;
    gap: 0;
}
.pt-step {
    display: flex;
    align-items: center;
    flex: 1;
}
.pt-dot {
    width: 32px; height: 32px;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.75rem;
    font-weight: 700;
    flex-shrink: 0;
}
.pt-dot-done { background: #D1FAE5; color: #065F46; border: 2px solid #6EE7B7; }
.pt-dot-active { background: #1151A6; color: white; border: 2px solid #1151A6; box-shadow: 0 0 0 4px rgba(17,81,166,0.15); }
.pt-dot-pending { background: #F1F5FD; color: #9CA3AF; border: 2px solid #E2E8F4; }
.pt-label { font-size: 0.75rem; font-weight: 500; margin-left: 0.5rem; }
.pt-label-done { color: #065F46; }
.pt-label-active { color: #1151A6; font-weight: 600; }
.pt-label-pending { color: #9CA3AF; }
.pt-line { flex: 1; height: 2px; background: #E2E8F4; margin: 0 0.5rem; }
.pt-line-done { background: #6EE7B7; }

/* ── Sidebar nav items ── */
.sb-logo {
    padding: 1.5rem 1.25rem 1rem;
    border-bottom: 1px solid #1E3A6E;
    margin-bottom: 0.5rem;
}
.sb-logo-text {
    font-size: 1.2rem;
    font-weight: 700;
    color: #FFFFFF !important;
    letter-spacing: -0.02em;
}
.sb-logo-sub {
    font-size: 0.7rem;
    color: #64748B !important;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-top: 0.1rem;
}
.sb-section-label {
    font-size: 0.65rem !important;
    font-weight: 600 !important;
    color: #4A5568 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.1em !important;
    padding: 0.75rem 1.25rem 0.25rem !important;
}
.sb-patient-card {
    margin: 0.75rem 1rem;
    background: #132847;
    border-radius: 12px;
    border: 1px solid #1E3A6E;
    padding: 1rem;
}
.sb-patient-name {
    font-size: 0.9rem !important;
    font-weight: 600 !important;
    color: #E2E8F0 !important;
    margin-bottom: 0.75rem;
}
.sb-score-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.35rem 0;
    border-bottom: 1px solid #1E3A6E;
}
.sb-score-label { font-size: 0.75rem !important; color: #94A3B8 !important; }
.sb-score-val { font-size: 0.78rem !important; font-weight: 600 !important; font-family: 'DM Mono', monospace !important; }
.sb-score-done { color: #34D399 !important; }
.sb-score-pending { color: #4B5563 !important; }

/* ── Forms ── */
.stTextInput > div > div > input,
.stNumberInput > div > div > input {
    border-radius: 10px !important;
    border: 1.5px solid #E2E8F4 !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.9rem !important;
    padding: 0.5rem 0.75rem !important;
    transition: border-color 0.15s !important;
}
.stTextInput > div > div > input:focus,
.stNumberInput > div > div > input:focus {
    border-color: #1151A6 !important;
    box-shadow: 0 0 0 3px rgba(17,81,166,0.1) !important;
}

/* ── Buttons ── */
.stButton > button {
    border-radius: 10px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
    padding: 0.55rem 1.25rem !important;
    transition: all 0.15s ease !important;
    border: 1.5px solid transparent !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #1151A6, #2563EB) !important;
    color: white !important;
    box-shadow: 0 2px 8px rgba(17,81,166,0.3) !important;
}
.stButton > button[kind="primary"]:hover {
    box-shadow: 0 4px 16px rgba(17,81,166,0.4) !important;
    transform: translateY(-1px) !important;
}
.stButton > button[kind="secondary"] {
    background: white !important;
    color: #1151A6 !important;
    border-color: #BFDBFE !important;
}

/* ── File uploader ── */
[data-testid="stFileUploader"] {
    border-radius: 14px !important;
    border: 2px dashed #BFDBFE !important;
    background: #F8FAFF !important;
    padding: 1rem !important;
}

/* ── Expander ── */
.streamlit-expanderHeader {
    background: #F8FAFF !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    color: #1A2340 !important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 0.5rem;
    background: #F1F5FD;
    border-radius: 10px;
    padding: 0.25rem;
    border: none;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 500 !important;
    font-size: 0.88rem !important;
    color: #6B7A99 !important;
    padding: 0.45rem 1rem !important;
}
.stTabs [aria-selected="true"] {
    background: white !important;
    color: #1151A6 !important;
    font-weight: 600 !important;
    box-shadow: 0 1px 4px rgba(11,30,61,0.1) !important;
}

/* ── Divider ── */
hr { border-color: #E2E8F4 !important; margin: 1.25rem 0 !important; }

/* ── Login page ── */
.login-wrap {
    max-width: 440px;
    margin: 3rem auto;
}
.login-header {
    text-align: center;
    margin-bottom: 2rem;
}
.login-logo { font-size: 3rem; margin-bottom: 0.5rem; }
.login-title { font-size: 1.75rem; font-weight: 700; color: #1A2340; margin: 0; }
.login-sub { font-size: 0.9rem; color: #6B7A99; margin-top: 0.35rem; }

/* ── History table ── */
.hist-row {
    background: #FFFFFF;
    border-radius: 12px;
    border: 1px solid #E2E8F4;
    padding: 1rem 1.25rem;
    margin-bottom: 0.75rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    transition: box-shadow 0.15s;
}
.hist-row:hover { box-shadow: 0 2px 12px rgba(11,30,61,0.08); }
.hist-name { font-weight: 600; font-size: 0.95rem; color: #1A2340; }
.hist-date { font-size: 0.78rem; color: #9CA3AF; margin-top: 0.15rem; }
.hist-badge {
    padding: 0.3rem 0.8rem;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 600;
}

/* ── Result score ring ── */
.result-wrap { text-align: center; padding: 1.5rem; }
.result-score-big {
    font-size: 3.5rem;
    font-weight: 700;
    font-family: 'DM Mono', monospace;
    line-height: 1;
    margin-bottom: 0.5rem;
}
.result-score-high { color: #DC2626; }
.result-score-moderate { color: #D97706; }
.result-score-low { color: #059669; }

/* ── Info box ── */
.info-box {
    background: #EFF6FF;
    border: 1px solid #BFDBFE;
    border-left: 4px solid #1151A6;
    border-radius: 10px;
    padding: 0.85rem 1rem;
    font-size: 0.85rem;
    color: #1E40AF;
    margin-bottom: 1rem;
}

/* ── Metric row ── */
.metric-row {
    display: flex;
    gap: 1rem;
    margin-bottom: 1rem;
}

/* ── Alert override ── */
[data-testid="stAlert"] { border-radius: 10px !important; }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════
def render_sidebar():
    with st.sidebar:
        # Logo
        st.markdown("""
        <div class="sb-logo">
            <div class="sb-logo-text">🧠 NeuroScreen</div>
            <div class="sb-logo-sub">Parkinson's Screening</div>
        </div>
        """, unsafe_allow_html=True)

        if st.session_state.token is None:
            st.markdown('<div class="sb-section-label">Navigation</div>', unsafe_allow_html=True)
            st.markdown("Please log in to continue.", unsafe_allow_html=True)
            return

        # User info
        uname = st.session_state.username or "User"
        initials = uname[:2].upper()
        st.markdown(f"""
        <div style="padding: 0.5rem 1rem 0.75rem; display:flex; align-items:center; gap:0.75rem; border-bottom:1px solid #1E3A6E; margin-bottom:0.5rem;">
            <div style="width:36px;height:36px;background:linear-gradient(135deg,#1151A6,#3B82F6);border-radius:50%;
                        display:flex;align-items:center;justify-content:center;font-size:0.8rem;font-weight:700;color:white;flex-shrink:0;">
                {initials}
            </div>
            <div>
                <div style="font-size:0.88rem;font-weight:600;color:#E2E8F0;">{uname}</div>
                <div style="font-size:0.72rem;color:#64748B;">Clinician</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Nav
        st.markdown('<div class="sb-section-label">Main Menu</div>', unsafe_allow_html=True)

        nav_items = [
            ("🏠", "Dashboard", "home"),
            ("🎙️", "Speech", "speech"),
            ("✍️", "Handwriting", "handwriting"),
            ("🧠", "EEG", "eeg"),
            ("📋", "Patient History", "history"),
        ]
        for icon, label, page in nav_items:
            is_active = st.session_state.page == page
            btn_style = "background:#1151A6;color:white;" if is_active else ""
            if st.button(f"{icon}  {label}", key=f"nav_{page}",
                         use_container_width=True):
                go(page)

        # Current patient session
        st.markdown('<div class="sb-section-label" style="margin-top:0.5rem;">Current Session</div>',
                    unsafe_allow_html=True)

        scores = st.session_state.scores
        pname  = st.session_state.patient_name or "No patient selected"

        def score_html(key, label, icon):
            v = scores.get(key)
            if v is not None:
                return f"""
                <div class="sb-score-row">
                    <span class="sb-score-label">{icon} {label}</span>
                    <span class="sb-score-val sb-score-done">{v:.3f} ✓</span>
                </div>"""
            return f"""
                <div class="sb-score-row">
                    <span class="sb-score-label">{icon} {label}</span>
                    <span class="sb-score-val sb-score-pending">—</span>
                </div>"""

        st.markdown(f"""
        <div class="sb-patient-card">
            <div class="sb-patient-name">👤 {pname}</div>
            {score_html("speech", "Speech", "🎙️")}
            {score_html("hw", "Handwriting", "✍️")}
            {score_html("eeg", "EEG", "🧠")}
        </div>
        """, unsafe_allow_html=True)

        # Tests complete counter
        done = sum(1 for v in scores.values() if v is not None)
        if done > 0:
            st.markdown(f"""
            <div style="margin:0 1rem 0.5rem;padding:0.65rem 0.9rem;background:#132847;border-radius:10px;
                        border:1px solid #1E3A6E;display:flex;justify-content:space-between;align-items:center;">
                <span style="font-size:0.78rem;color:#94A3B8;">Tests complete</span>
                <span style="font-size:0.85rem;font-weight:700;color:#34D399;">{done}/3</span>
            </div>
            """, unsafe_allow_html=True)

            if st.button("⚡  Get Fused Result", use_container_width=True, key="nav_fuse"):
                go("fuse")

        st.markdown("<div style='flex:1'></div>", unsafe_allow_html=True)
        st.markdown("---")
        if st.button("🚪  Logout", use_container_width=True, key="nav_logout"):
            for k in ["token", "username", "patient_name", "patient_id", "last_result"]:
                st.session_state[k] = None
            st.session_state.scores  = {"speech": None, "hw": None, "eeg": None}
            st.session_state.page    = "login"
            st.rerun()


# ═══════════════════════════════════════════════════════════
# TOPBAR
# ═══════════════════════════════════════════════════════════
PAGE_META = {
    "home":        ("Dashboard", "Overview & screening tests"),
    "speech":      ("Speech Analysis", "Voice biomarker screening"),
    "handwriting": ("Handwriting Analysis", "Motor control screening"),
    "eeg":         ("EEG Analysis", "Brainwave pattern screening"),
    "fuse":        ("Fused Assessment", "Combined risk evaluation"),
    "history":     ("Patient History", "Past screening records"),
}

def render_topbar():
    page  = st.session_state.page
    title, sub = PAGE_META.get(page, ("NeuroScreen", ""))
    uname = st.session_state.username or ""
    initials = uname[:2].upper()

    st.markdown(f"""
    <div class="topbar">
        <div class="topbar-left">
            <span class="topbar-breadcrumb">NeuroScreen /</span>
            <span class="topbar-page">{title}</span>
        </div>
        <div class="user-chip">
            <div class="user-avatar">{initials}</div>
            <span class="user-name">{uname}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
# PROGRESS TRACKER
# ═══════════════════════════════════════════════════════════
def render_progress():
    scores = st.session_state.scores
    steps  = [
        ("speech", "Speech", "🎙️"),
        ("hw",     "Handwriting", "✍️"),
        ("eeg",    "EEG", "🧠"),
        ("fuse",   "Fused Result", "⚡"),
    ]
    page   = st.session_state.page
    active_map = {"speech": 0, "handwriting": 1, "eeg": 2, "fuse": 3}
    active_idx = active_map.get(page, -1)

    parts = []
    for i, (key, label, icon) in enumerate(steps):
        is_done   = (key != "fuse" and scores.get(key) is not None) or \
                    (key == "fuse" and st.session_state.last_result is not None)
        is_active = (i == active_idx)

        if is_done:
            dot_cls = "pt-dot-done"; lbl_cls = "pt-label-done"; dot_content = "✓"
        elif is_active:
            dot_cls = "pt-dot-active"; lbl_cls = "pt-label-active"; dot_content = str(i+1)
        else:
            dot_cls = "pt-dot-pending"; lbl_cls = "pt-label-pending"; dot_content = str(i+1)

        parts.append(f"""
        <div class="pt-step">
            <div class="pt-dot {dot_cls}">{dot_content}</div>
            <span class="pt-label {lbl_cls}">{icon} {label}</span>
        </div>""")

        if i < len(steps) - 1:
            line_cls = "pt-line-done" if is_done else "pt-line"
            parts.append(f'<div class="pt-line {line_cls}"></div>')

    st.markdown(f'<div class="progress-tracker">{"".join(parts)}</div>',
                unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
# RISK DISPLAY helper
# ═══════════════════════════════════════════════════════════
def render_risk_result(p_pd, risk, label="PD Probability"):
    score_cls = {
        "High Risk":     "result-score-high",
        "Moderate Risk": "result-score-moderate",
        "Low Risk":      "result-score-low",
    }.get(risk, "result-score-low")

    risk_cls = {
        "High Risk":     "risk-high",
        "Moderate Risk": "risk-moderate",
        "Low Risk":      "risk-low",
    }.get(risk, "risk-low")

    icon = {"High Risk": "⚠️", "Moderate Risk": "⚡", "Low Risk": "✅"}.get(risk, "")

    st.markdown(f"""
    <div class="ns-card" style="text-align:center;padding:2rem;">
        <div style="font-size:0.8rem;font-weight:500;color:#6B7A99;text-transform:uppercase;
                    letter-spacing:0.08em;margin-bottom:0.5rem;">{label}</div>
        <div class="result-score-big {score_cls}">{p_pd:.1%}</div>
        <div class="{risk_cls}" style="margin-top:1rem;display:inline-block;">
            {icon} {risk}
        </div>
    </div>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
# LOGIN PAGE
# ═══════════════════════════════════════════════════════════
def show_login():
    col_l, col_c, col_r = st.columns([1, 1.4, 1])
    with col_c:
        st.markdown("""
        <div class="login-header">
            <div class="login-logo">🧠</div>
            <h1 class="login-title">NeuroScreen</h1>
            <p class="login-sub">Parkinson's Disease Cross-Modal Screening</p>
        </div>
        """, unsafe_allow_html=True)

        with st.container():
            tab1, tab2 = st.tabs(["  Sign In  ", "  Create Account  "])

            with tab1:
                st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
                email    = st.text_input("Email address", placeholder="you@hospital.org", key="li_email")
                password = st.text_input("Password", type="password", placeholder="••••••••", key="li_pass")
                st.markdown("<div style='height:0.25rem'></div>", unsafe_allow_html=True)
                if st.button("Sign In →", use_container_width=True, type="primary", key="li_btn"):
                    if not email or not password:
                        st.error("Please enter your email and password.")
                    else:
                        with st.spinner("Signing in…"):
                            res = requests.post(f"{BASE_URL}/auth/login",
                                                json={"email": email, "password": password})
                        if res.status_code == 200:
                            d = res.json()
                            st.session_state.token    = d["token"]
                            st.session_state.username = d["username"]
                            st.session_state.page     = "home"
                            st.rerun()
                        else:
                            try:    st.error(res.json().get("detail", "Login failed"))
                            except: st.error(f"Login failed ({res.status_code})")

            with tab2:
                st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
                username = st.text_input("Full name", placeholder="Dr. Jane Smith", key="reg_user")
                email    = st.text_input("Email address", placeholder="you@hospital.org", key="reg_email")
                password = st.text_input("Password", type="password", placeholder="Min. 8 characters", key="reg_pass")
                st.markdown("<div style='height:0.25rem'></div>", unsafe_allow_html=True)
                if st.button("Create Account →", use_container_width=True, type="primary", key="reg_btn"):
                    if not username or not email or not password:
                        st.error("Please fill in all fields.")
                    else:
                        with st.spinner("Creating account…"):
                            res = requests.post(f"{BASE_URL}/auth/register",
                                                json={"username": username, "email": email, "password": password})
                        if res.status_code == 200:
                            st.success("Account created! Please sign in.")
                        else:
                            try:    st.error(res.json().get("detail", "Registration failed"))
                            except: st.error(f"Registration failed ({res.status_code})")

        st.markdown("""
        <div style="text-align:center;margin-top:2rem;font-size:0.78rem;color:#9CA3AF;">
            NeuroScreen v1.0 · For clinical research use only
        </div>
        """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
# HOME / DASHBOARD
# ═══════════════════════════════════════════════════════════
def show_home():
    render_topbar()

    # Patient name input (top of flow)
    pname = st.session_state.patient_name
    col1, col2 = st.columns([3, 1])
    with col1:
        new_name = st.text_input(
            "Patient Name",
            value=pname,
            placeholder="Enter patient name before starting tests…",
            key="home_pname",
            label_visibility="collapsed"
        )
        if new_name != pname:
            st.session_state.patient_name = new_name
    with col2:
        if not st.session_state.patient_name:
            st.markdown("""
            <div style="padding:0.5rem 0;font-size:0.82rem;color:#D97706;">
                ⚠️ Enter patient name first
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="padding:0.5rem 0;font-size:0.82rem;color:#059669;">
                ✓ Patient: <b>{st.session_state.patient_name}</b>
            </div>
            """, unsafe_allow_html=True)

    # Stats row
    scores = st.session_state.scores
    done   = sum(1 for v in scores.values() if v is not None)
    c1, c2, c3, c4 = st.columns(4)
    stats = [
        (c1, str(done), "Tests Complete"),
        (c2, f"{scores['speech']:.3f}" if scores['speech'] else "—", "Speech Score"),
        (c3, f"{scores['hw']:.3f}"     if scores['hw']     else "—", "Handwriting Score"),
        (c4, f"{scores['eeg']:.3f}"    if scores['eeg']    else "—", "EEG Score"),
    ]
    for col, num, label in stats:
        with col:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-num">{num}</div>
                <div class="stat-label">{label}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='height:1.25rem'></div>", unsafe_allow_html=True)
    st.markdown("#### Select a Screening Test")

    # Modality cards
    c1, c2, c3 = st.columns(3)
    modalities = [
        (c1, "speech",      "speech", "🎙️", "Speech Analysis",
         "Analyse voice biomarkers including jitter, shimmer, HNR, and MFCC features.",
         "Upload CSV"),
        (c2, "handwriting", "hw",     "✍️", "Handwriting Analysis",
         "Detect motor control abnormalities from spiral or wave drawing images.",
         "Upload Image"),
        (c3, "eeg",         "eeg",    "🧠", "EEG Analysis",
         "Screen brainwave patterns for Parkinson's-related neural signatures.",
         "Upload ZIP"),
    ]
    for col, page_key, score_key, icon, title, desc, action in modalities:
        with col:
            badge = (f'<span class="modality-badge badge-done">✓ Score: {scores[score_key]:.3f}</span>'
                     if scores[score_key] is not None
                     else f'<span class="modality-badge badge-pending">Pending</span>')
            st.markdown(f"""
            <div class="modality-card">
                <div class="modality-icon">{icon}</div>
                <div class="modality-title">{title}</div>
                <div class="modality-desc">{desc}</div>
                {badge}
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"{action} →", key=f"go_{page_key}", use_container_width=True):
                if not st.session_state.patient_name:
                    st.warning("Please enter a patient name first.")
                else:
                    go(page_key)

    # Fuse button if any scores exist
    if done > 0:
        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
        st.markdown("---")
        col_l, col_m, col_r = st.columns([1, 2, 1])
        with col_m:
            st.markdown(f"""
            <div style="text-align:center;margin-bottom:0.75rem;">
                <span style="font-size:0.85rem;color:#6B7A99;">
                    {done}/3 test(s) complete · Fused score uses available results
                </span>
            </div>
            """, unsafe_allow_html=True)
            if st.button("⚡ Calculate Fused Risk Score →",
                         use_container_width=True, type="primary", key="home_fuse"):
                go("fuse")


# ═══════════════════════════════════════════════════════════
# SPEECH
# ═══════════════════════════════════════════════════════════
def show_speech():
    render_topbar()
    render_progress()

    st.markdown("""
    <div class="page-header">
        <div class="page-header-icon">🎙️</div>
        <div>
            <h1>Speech Analysis</h1>
            <p>Upload voice feature CSV or enter values manually</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["  📁 Upload CSV  ", "  ✏️ Enter Manually  "])

    with tab1:
        st.markdown("""
        <div class="info-box">
            Upload a CSV with 22 voice feature columns. The file should have a single data row
            with headers matching the standard Parkinson's voice dataset features.
        </div>
        """, unsafe_allow_html=True)

        uploaded = st.file_uploader("Drop CSV here or click to browse",
                                    type=["csv"], key="sp_csv")
        if uploaded:
            df  = pd.read_csv(io.BytesIO(uploaded.getvalue()))
            row = df.iloc[0].to_dict()
            st.markdown(f"""
            <div style="background:#F0FDF4;border:1px solid #A7F3D0;border-radius:10px;
                        padding:0.75rem 1rem;font-size:0.83rem;color:#065F46;margin-bottom:1rem;">
                ✓ File loaded — <b>{uploaded.name}</b> · {len(df.columns)} columns detected
            </div>
            """, unsafe_allow_html=True)

            with st.expander("Preview feature values"):
                preview_df = pd.DataFrame([row]).T.reset_index()
                preview_df.columns = ["Feature", "Value"]
                st.dataframe(preview_df, use_container_width=True, height=300)

            if st.button("Run Speech Analysis →", type="primary", key="sp_csv_btn"):
                with st.spinner("Analysing…"):
                    res = requests.post(f"{BASE_URL}/analyze/speech",
                                        json=row, headers=auth_header())
                if res.status_code == 200:
                    d = res.json()
                    st.session_state.scores["speech"] = d["p_pd"]
                    render_risk_result(d["p_pd"], d["risk"], "Speech — PD Probability")
                    st.success("Score saved to session. Return to Dashboard to continue.")
                else:
                    st.error(f"Analysis failed: {res.text}")

    with tab2:
        st.markdown("""
        <div class="info-box">
            Enter all 22 acoustic feature values below. Use precise decimal values
            from your voice analysis software.
        </div>
        """, unsafe_allow_html=True)

        features = [
            "MDVP:Fo(Hz)", "MDVP:Fhi(Hz)", "MDVP:Flo(Hz)", "MDVP:Jitter(%)",
            "MDVP:Jitter(Abs)", "MDVP:RAP", "MDVP:PPQ", "Jitter:DDP",
            "MDVP:Shimmer", "MDVP:Shimmer(dB)", "Shimmer:APQ3", "Shimmer:APQ5",
            "MDVP:APQ", "Shimmer:DDA", "NHR", "HNR", "RPDE", "DFA",
            "spread1", "spread2", "D2", "PPE"
        ]
        vals = {}
        cols = st.columns(3)
        for i, f in enumerate(features):
            with cols[i % 3]:
                vals[f] = st.number_input(f, value=0.0, format="%.6f",
                                          key=f"sp_man_{f}")

        if st.button("Run Speech Analysis →", type="primary", key="sp_man_btn"):
            with st.spinner("Analysing…"):
                res = requests.post(f"{BASE_URL}/analyze/speech",
                                    json=vals, headers=auth_header())
            if res.status_code == 200:
                d = res.json()
                st.session_state.scores["speech"] = d["p_pd"]
                render_risk_result(d["p_pd"], d["risk"], "Speech — PD Probability")
                st.success("Score saved to session. Return to Dashboard to continue.")
            else:
                st.error(f"Analysis failed: {res.text}")

    st.markdown("---")
    if st.button("← Back to Dashboard", key="sp_back"):
        go("home")


# ═══════════════════════════════════════════════════════════
# HANDWRITING
# ═══════════════════════════════════════════════════════════
def show_handwriting():
    render_topbar()
    render_progress()

    st.markdown("""
    <div class="page-header">
        <div class="page-header-icon">✍️</div>
        <div>
            <h1>Handwriting Analysis</h1>
            <p>Upload a spiral or wave drawing image for motor assessment</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="info-box">
        Upload a JPG or PNG of the patient's handwriting sample (spiral/wave test).
        The image will be resized automatically before analysis.
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1.4, 1])
    with col1:
        uploaded = st.file_uploader("Drop image here or click to browse",
                                    type=["jpg", "jpeg", "png"], key="hw_img")
    with col2:
        if uploaded:
            st.image(uploaded, caption="Uploaded image", use_container_width=True)

    if uploaded:
        if st.button("Run Handwriting Analysis →", type="primary", key="hw_btn"):
            with st.spinner("Analysing image…"):
                res = requests.post(
                    f"{BASE_URL}/analyze/handwriting",
                    files={"image": (uploaded.name, uploaded.getvalue(), uploaded.type)},
                    headers=auth_header()
                )
            if res.status_code == 200:
                d = res.json()
                st.session_state.scores["hw"] = d["p_pd"]
                render_risk_result(d["p_pd"], d["risk"], "Handwriting — PD Probability")
                st.success("Score saved to session. Return to Dashboard to continue.")
            else:
                st.error(f"Analysis failed: {res.text}")

    st.markdown("---")
    if st.button("← Back to Dashboard", key="hw_back"):
        go("home")


# ═══════════════════════════════════════════════════════════
# EEG
# ═══════════════════════════════════════════════════════════
def show_eeg():
    render_topbar()
    render_progress()

    st.markdown("""
    <div class="page-header">
        <div class="page-header-icon">🧠</div>
        <div>
            <h1>EEG Analysis</h1>
            <p>Upload a BIDS-format ZIP containing an EEGLAB .set file</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="info-box">
        Upload a ZIP file containing the EEG recording in EEGLAB format (.set file inside).
        Resting-state recordings are preferred. The system will preprocess and extract features automatically.
    </div>
    """, unsafe_allow_html=True)

    uploaded = st.file_uploader("Drop ZIP here or click to browse",
                                type=["zip"], key="eeg_zip")
    if uploaded:
        st.markdown(f"""
        <div style="background:#F0FDF4;border:1px solid #A7F3D0;border-radius:10px;
                    padding:0.75rem 1rem;font-size:0.83rem;color:#065F46;margin-bottom:1rem;">
            ✓ File loaded — <b>{uploaded.name}</b> · {len(uploaded.getvalue())//1024} KB
        </div>
        """, unsafe_allow_html=True)

        if st.button("Run EEG Analysis →", type="primary", key="eeg_btn"):
            with st.spinner("Processing EEG data… this may take a moment"):
                res = requests.post(
                    f"{BASE_URL}/analyze/eeg",
                    files={"eeg_zip": (uploaded.name,
                                       uploaded.getvalue(),
                                       "application/zip")},
                    headers=auth_header()
                )
            if res.status_code == 200:
                d = res.json()
                st.session_state.scores["eeg"] = d["p_pd"]
                render_risk_result(d["p_pd"], d["risk"], "EEG — PD Probability")
                if d.get("n_segs"):
                    st.markdown(f"""
                    <div style="text-align:center;font-size:0.8rem;color:#6B7A99;margin-top:0.5rem;">
                        Analysed across {d['n_segs']} EEG segments · Model: {d.get('model','—')}
                    </div>
                    """, unsafe_allow_html=True)
                st.success("Score saved to session. Return to Dashboard to continue.")
            else:
                st.error(f"Analysis failed: {res.text}")

    st.markdown("---")
    if st.button("← Back to Dashboard", key="eeg_back"):
        go("home")


# ═══════════════════════════════════════════════════════════
# FUSE
# ═══════════════════════════════════════════════════════════
def show_fuse():
    render_topbar()
    render_progress()

    st.markdown("""
    <div class="page-header">
        <div class="page-header-icon">⚡</div>
        <div>
            <h1>Fused Risk Assessment</h1>
            <p>Weighted combination of available modality scores (1–3 tests)</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Helper: compute fused score locally from whatever scores exist ──
    WEIGHTS = {"speech": 0.30, "hw": 0.25, "eeg": 0.45}

    def local_fuse(sc):
        available = {k: v for k, v in sc.items() if v is not None}
        if not available:
            return None, None
        total_w = sum(WEIGHTS[k] for k in available)
        fused = sum(WEIGHTS[k] * v for k, v in available.items()) / total_w
        if fused >= 0.65:
            risk = "High Risk"
        elif fused >= 0.40:
            risk = "Moderate Risk"
        else:
            risk = "Low Risk"
        return fused, risk

    # ── If we just saved a result, show it immediately (scores already cleared) ──
    if st.session_state.last_result:
        d     = st.session_state.last_result
        fused = d.get("fused_score")
        risk  = d.get("risk")

        # Show the scores that were used (stored alongside result)
        saved_scores = d.get("used_scores", {})
        if saved_scores:
            col1, col2, col3 = st.columns(3)
            modal_info = [
                (col1, "speech", "🎙️", "Speech"),
                (col2, "hw",     "✍️", "Handwriting"),
                (col3, "eeg",    "🧠", "EEG"),
            ]
            available_keys = [k for k in WEIGHTS if saved_scores.get(k) is not None]
            raw_total = sum(WEIGHTS[k] for k in available_keys) if available_keys else 1
            for col, key, icon, label in modal_info:
                with col:
                    val   = saved_scores.get(key)
                    base_w = int(WEIGHTS[key] * 100)
                    eff_w  = int(WEIGHTS[key] / raw_total * 100)
                    if val is not None:
                        colour = "#DC2626" if val >= 0.65 else "#D97706" if val >= 0.40 else "#059669"
                        wlabel = f"Effective weight: {eff_w}%" if len(available_keys) < 3 else f"Weight: {base_w}%"
                        st.markdown(f"""
                        <div class="ns-card" style="text-align:center;">
                            <div style="font-size:1.5rem">{icon}</div>
                            <div style="font-size:0.78rem;color:#6B7A99;font-weight:500;
                                        text-transform:uppercase;letter-spacing:0.06em;margin:0.4rem 0;">{label}</div>
                            <div style="font-size:1.75rem;font-weight:700;font-family:'DM Mono',monospace;color:{colour};">{val:.3f}</div>
                            <div style="font-size:0.72rem;color:#9CA3AF;margin-top:0.25rem;">{wlabel}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div class="ns-card" style="text-align:center;opacity:0.45;">
                            <div style="font-size:1.5rem">{icon}</div>
                            <div style="font-size:0.78rem;color:#6B7A99;font-weight:500;
                                        text-transform:uppercase;letter-spacing:0.06em;margin:0.4rem 0;">{label}</div>
                            <div style="font-size:1.1rem;color:#9CA3AF;">Not tested</div>
                            <div style="font-size:0.72rem;color:#9CA3AF;margin-top:0.25rem;">Skipped</div>
                        </div>
                        """, unsafe_allow_html=True)
            st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

        render_risk_result(fused, risk, "Fused Risk Score")
        st.markdown(f"""
        <div style="text-align:center;font-size:0.82rem;color:#6B7A99;margin-top:0.5rem;">
            Record saved · Patient: <b>{d.get('patient_name','—')}</b> · ID: {d.get('patient_id','—')}
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("🔄 Start New Patient", use_container_width=True, key="fuse_new"):
                st.session_state.last_result = None
                go("home")
        with col_b:
            if st.button("📋 View History", use_container_width=True, key="fuse_hist"):
                st.session_state.last_result  = None
                st.session_state.history_cache = None
                go("history")
        st.markdown("---")
        if st.button("← Back to Dashboard", key="fuse_back"):
            go("home")
        return   # ← stop here; nothing else to render

    # ── Normal pre-submission flow ──
    scores = st.session_state.scores
    pname  = st.session_state.patient_name

    done = sum(1 for v in scores.values() if v is not None)

    if done == 0:
        st.warning("No test scores available. Please run at least one screening test first.")
        if st.button("← Back to Dashboard", key="fuse_back_empty"):
            go("home")
        return

    # Score summary cards
    available_keys = [k for k in WEIGHTS if scores.get(k) is not None]
    raw_total = sum(WEIGHTS[k] for k in available_keys)

    col1, col2, col3 = st.columns(3)
    modal_info = [
        (col1, "speech", "🎙️", "Speech"),
        (col2, "hw",     "✍️", "Handwriting"),
        (col3, "eeg",    "🧠", "EEG"),
    ]
    for col, key, icon, label in modal_info:
        with col:
            val    = scores.get(key)
            base_w = int(WEIGHTS[key] * 100)
            eff_w  = int(WEIGHTS[key] / raw_total * 100)
            if val is not None:
                colour = "#DC2626" if val >= 0.65 else "#D97706" if val >= 0.40 else "#059669"
                wlabel = f"Effective weight: {eff_w}%" if len(available_keys) < 3 else f"Weight: {base_w}%"
                st.markdown(f"""
                <div class="ns-card" style="text-align:center;">
                    <div style="font-size:1.5rem">{icon}</div>
                    <div style="font-size:0.78rem;color:#6B7A99;font-weight:500;
                                text-transform:uppercase;letter-spacing:0.06em;margin:0.4rem 0;">{label}</div>
                    <div style="font-size:1.75rem;font-weight:700;font-family:'DM Mono',monospace;color:{colour};">{val:.3f}</div>
                    <div style="font-size:0.72rem;color:#9CA3AF;margin-top:0.25rem;">{wlabel}</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="ns-card" style="text-align:center;opacity:0.45;">
                    <div style="font-size:1.5rem">{icon}</div>
                    <div style="font-size:0.78rem;color:#6B7A99;font-weight:500;
                                text-transform:uppercase;letter-spacing:0.06em;margin:0.4rem 0;">{label}</div>
                    <div style="font-size:1.1rem;color:#9CA3AF;">Not tested</div>
                    <div style="font-size:0.72rem;color:#9CA3AF;margin-top:0.25rem;">Base weight: {base_w}% (skipped)</div>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    # ── Live preview of fused score ──
    fused_preview, risk_preview = local_fuse(scores)
    if fused_preview is not None:
        st.markdown("<div style='margin-bottom:0.5rem;'></div>", unsafe_allow_html=True)
        render_risk_result(fused_preview, risk_preview, f"Preview — Fused Score ({done}/3 tests)")

    # Patient confirmation
    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
    if not pname:
        new_pname = st.text_input("Patient Name (required to save)",
                                  placeholder="Enter patient name…",
                                  key="fuse_pname")
        if new_pname:
            st.session_state.patient_name = new_pname
    else:
        st.markdown(f"""
        <div style="background:#EFF6FF;border:1px solid #BFDBFE;border-radius:10px;
                    padding:0.75rem 1rem;font-size:0.88rem;color:#1E40AF;margin-bottom:1rem;">
            👤 Patient: <b>{pname}</b>
        </div>
        """, unsafe_allow_html=True)

    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        if st.button("💾 Save Result →",
                     use_container_width=True, type="primary", key="fuse_btn"):
            if not st.session_state.patient_name:
                st.error("Please enter a patient name before saving.")
            else:
                # Snapshot scores and patient name BEFORE clearing
                snapshot_scores  = dict(scores)
                snapshot_pname   = st.session_state.patient_name
                fused_val, risk_val = local_fuse(snapshot_scores)

                # Try to save to backend; if it fails, still show local result
                saved_pid = None
                try:
                    with st.spinner("Saving…"):
                        res = requests.post(
                            f"{BASE_URL}/analyze/fuse",
                            json={"patient_name": snapshot_pname,
                                  "scores": snapshot_scores},
                            headers=auth_header(),
                            timeout=8
                        )
                    if res.status_code == 200:
                        d = res.json()
                        saved_pid  = d.get("patient_id")
                        fused_val  = d.get("fused_score", fused_val)
                        risk_val   = d.get("risk", risk_val)
                except Exception:
                    pass  # backend down — still show local result

                st.session_state.last_result = {
                    "fused_score":  fused_val,
                    "risk":         risk_val,
                    "patient_name": snapshot_pname,
                    "patient_id":   saved_pid,
                    "used_scores":  snapshot_scores,
                }
                # Now safe to clear for next patient
                st.session_state.scores       = {"speech": None, "hw": None, "eeg": None}
                st.session_state.patient_name = ""
                st.rerun()

    st.markdown("---")
    if st.button("← Back to Dashboard", key="fuse_back"):
        go("home")


# ═══════════════════════════════════════════════════════════
# HISTORY
# ═══════════════════════════════════════════════════════════
def show_history():
    render_topbar()

    st.markdown("""
    <div class="page-header">
        <div class="page-header-icon">📋</div>
        <div>
            <h1>Patient History</h1>
            <p>All screening records for your account</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_refresh, _ = st.columns([1, 4])
    with col_refresh:
        if st.button("🔄 Refresh", key="hist_refresh"):
            st.session_state.history_cache = None

    if st.session_state.history_cache is None:
        with st.spinner("Loading records…"):
            res = requests.get(f"{BASE_URL}/history/all/mine",
                               headers=auth_header())
        if res.status_code == 200:
            st.session_state.history_cache = res.json()
        else:
            st.error("Could not fetch history.")
            if st.button("← Back to Dashboard"):
                go("home")
            return

    records = st.session_state.history_cache

    if not records:
        st.markdown("""
        <div class="ns-card" style="text-align:center;padding:3rem;color:#6B7A99;">
            <div style="font-size:2.5rem;margin-bottom:1rem;">📭</div>
            <div style="font-weight:600;font-size:1rem;">No records yet</div>
            <div style="font-size:0.85rem;margin-top:0.5rem;">
                Complete a screening and save a result to see it here.
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Summary stats
        total = len(records)
        all_results = [r for rec in records for r in rec.get("screening_results", [])]
        high   = sum(1 for r in all_results if r.get("risk_label") == "High Risk")
        mod    = sum(1 for r in all_results if r.get("risk_label") == "Moderate Risk")
        low    = sum(1 for r in all_results if r.get("risk_label") == "Low Risk")

        c1, c2, c3, c4 = st.columns(4)
        for col, num, label in [
            (c1, total, "Total Patients"),
            (c2, high,  "High Risk"),
            (c3, mod,   "Moderate Risk"),
            (c4, low,   "Low Risk"),
        ]:
            with col:
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-num">{num}</div>
                    <div class="stat-label">{label}</div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("<div style='height:1.25rem'></div>", unsafe_allow_html=True)

        # Search
        search = st.text_input("🔍 Search by patient name",
                               placeholder="Type to filter…", key="hist_search")

        filtered = [r for r in records
                    if search.lower() in r.get("patient_name", "").lower()]

        if not filtered:
            st.info("No records match your search.")
        else:
            for rec in filtered:
                pname   = rec.get("patient_name", "Unknown")
                date    = rec.get("created_at", "")[:10] if rec.get("created_at") else "—"
                results = rec.get("screening_results", [])

                with st.expander(f"👤  {pname}   ·   {date}   ·   {len(results)} result(s)"):
                    if not results:
                        st.write("No results recorded.")
                    for i, r in enumerate(results):
                        fused  = r.get("fused_score")
                        risk   = r.get("risk_label", "—")
                        risk_cls = {
                            "High Risk": "risk-high",
                            "Moderate Risk": "risk-moderate",
                            "Low Risk": "risk-low"
                        }.get(risk, "")

                        col1, col2, col3 = st.columns([2, 2, 1])
                        with col1:
                            eeg  = r.get("eeg_score")
                            sp   = r.get("speech_score")
                            hw   = r.get("hw_score")
                            st.markdown(f"""
                            <div style="font-size:0.83rem;">
                                <span class="score-pill">🧠 EEG: {f"{eeg:.3f}" if eeg else "—"}</span>&nbsp;
                                <span class="score-pill">🎙️ Speech: {f"{sp:.3f}" if sp else "—"}</span>&nbsp;
                                <span class="score-pill">✍️ HW: {f"{hw:.3f}" if hw else "—"}</span>
                            </div>
                            """, unsafe_allow_html=True)
                        with col2:
                            if fused is not None:
                                st.markdown(f"""
                                <div style="font-size:0.83rem;">
                                    Fused score:&nbsp;
                                    <span style="font-family:'DM Mono',monospace;font-weight:700;">
                                        {fused:.4f}
                                    </span>
                                </div>
                                """, unsafe_allow_html=True)
                        with col3:
                            st.markdown(f'<div class="{risk_cls}" style="font-size:0.78rem;">{risk}</div>',
                                        unsafe_allow_html=True)

                        if i < len(results) - 1:
                            st.divider()

    st.markdown("---")
    if st.button("← Back to Dashboard", key="hist_back"):
        go("home")


# ═══════════════════════════════════════════════════════════
# ROUTER
# ═══════════════════════════════════════════════════════════
render_sidebar()

if st.session_state.token is None:
    show_login()
else:
    page = st.session_state.page
    if   page == "home":        show_home()
    elif page == "speech":      show_speech()
    elif page == "handwriting":  show_handwriting()
    elif page == "eeg":         show_eeg()
    elif page == "fuse":        show_fuse()
    elif page == "history":     show_history()
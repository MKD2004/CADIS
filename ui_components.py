"""
ui_components.py — CADIS Premium Design System
================================================
All CSS, HTML component builders, and design tokens.
Import everything from here to keep app.py clean.
"""

import streamlit as st

# ═══════════════════════════════════════════════════════════════
#  DESIGN TOKENS
# ═══════════════════════════════════════════════════════════════
COLORS = {
    "bg_deep":      "#07090f",
    "bg_surface":   "#0d1117",
    "bg_card":      "#111827",
    "bg_card2":     "#161d2e",
    "border":       "#1e2d40",
    "cyan":         "#00e5ff",
    "cyan_dim":     "#00b8cc",
    "purple":       "#a855f7",
    "purple_dim":   "#7c3aed",
    "amber":        "#f59e0b",
    "green":        "#10b981",
    "red":          "#ef4444",
    "blue":         "#3b82f6",
    "text_primary": "#e2e8f0",
    "text_muted":   "#64748b",
    "text_dim":     "#94a3b8",
}

ENTITY_COLORS = {
    "PERSON":       ("#f59e0b", "#1c1400"),
    "ORGANIZATION": ("#a855f7", "#110a1f"),
    "LOCATION":     ("#10b981", "#071a12"),
    "DATE":         ("#3b82f6", "#050e1c"),
    "MONEY":        ("#00e5ff", "#001a1f"),
    "MISC":         ("#64748b", "#0d1117"),
}

# ═══════════════════════════════════════════════════════════════
#  GLOBAL CSS
# ═══════════════════════════════════════════════════════════════
GLOBAL_CSS = """
<style>
/* ── Google Fonts ─────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=JetBrains+Mono:wght@300;400;500;700&family=DM+Sans:wght@300;400;500&display=swap');

/* ── Kill Streamlit chrome ────────────────────────────── */
#MainMenu, footer, header { visibility: hidden !important; }
.stDeployButton { display: none !important; }
[data-testid="stToolbar"] { display: none !important; }

/* ── Root variables ──────────────────────────────────── */
:root {
  --bg-deep:      #07090f;
  --bg-surface:   #0d1117;
  --bg-card:      #111827;
  --bg-card2:     #161d2e;
  --border:       #1e2d40;
  --cyan:         #00e5ff;
  --cyan-dim:     rgba(0,229,255,0.08);
  --purple:       #a855f7;
  --purple-dim:   rgba(168,85,247,0.08);
  --amber:        #f59e0b;
  --amber-dim:    rgba(245,158,11,0.08);
  --green:        #10b981;
  --red:          #ef4444;
  --blue:         #3b82f6;
  --text:         #e2e8f0;
  --text-dim:     #94a3b8;
  --text-muted:   #64748b;
  --font-display: 'Syne', sans-serif;
  --font-mono:    'JetBrains Mono', monospace;
  --font-body:    'DM Sans', sans-serif;
  --r:            12px;
  --r-lg:         18px;
}

/* ── Global base ─────────────────────────────────────── */
html, body, .main, [data-testid="stAppViewContainer"] {
  background: var(--bg-deep) !important;
  color: var(--text) !important;
  font-family: var(--font-body) !important;
}
.block-container {
  padding: 1.5rem 2rem !important;
  max-width: 1300px !important;
}

/* ── Scrollbar ───────────────────────────────────────── */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: var(--bg-deep); }
::-webkit-scrollbar-thumb { background: #1e2d40; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: var(--cyan-dim); }

/* ── Sidebar ─────────────────────────────────────────── */
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #07090f 0%, #0a0f1e 60%, #07090f 100%) !important;
  border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] * { font-family: var(--font-body) !important; }
[data-testid="stSidebar"] .stTextArea textarea {
  background: #0d1117 !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--r) !important;
  color: var(--text-dim) !important;
  font-family: var(--font-mono) !important;
  font-size: 0.78rem !important;
  resize: none !important;
}
[data-testid="stSidebar"] .stTextArea textarea:focus {
  border-color: var(--cyan) !important;
  box-shadow: 0 0 0 2px rgba(0,229,255,0.15) !important;
}
[data-testid="stSidebar"] .stSelectbox select,
[data-testid="stSidebar"] [data-testid="stSelectbox"] > div {
  background: #0d1117 !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--r) !important;
  color: var(--text) !important;
}

/* ── Sidebar run button ──────────────────────────────── */
[data-testid="stSidebar"] .stButton > button[kind="primary"] {
  width: 100% !important;
  background: linear-gradient(135deg, #00b8cc, #0070ff) !important;
  color: #fff !important;
  font-family: var(--font-display) !important;
  font-weight: 700 !important;
  font-size: 0.9rem !important;
  letter-spacing: 1.5px !important;
  text-transform: uppercase !important;
  border: none !important;
  border-radius: var(--r) !important;
  padding: 0.65rem 1rem !important;
  transition: all 0.3s ease !important;
  box-shadow: 0 0 24px rgba(0,229,255,0.3) !important;
}
[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
  box-shadow: 0 0 40px rgba(0,229,255,0.55) !important;
  transform: translateY(-1px) !important;
}

/* ── Tabs ────────────────────────────────────────────── */
[data-testid="stTabs"] [role="tablist"] {
  background: var(--bg-surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: 50px !important;
  padding: 4px !important;
  gap: 2px !important;
  margin-bottom: 24px !important;
}
[data-testid="stTabs"] button[role="tab"] {
  border-radius: 50px !important;
  padding: 8px 18px !important;
  font-family: var(--font-body) !important;
  font-size: 0.82rem !important;
  font-weight: 500 !important;
  color: var(--text-muted) !important;
  border: none !important;
  background: transparent !important;
  transition: all 0.25s ease !important;
  letter-spacing: 0.3px !important;
}
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
  background: linear-gradient(135deg, rgba(0,229,255,0.15), rgba(168,85,247,0.15)) !important;
  color: var(--cyan) !important;
  border: 1px solid rgba(0,229,255,0.3) !important;
}
[data-testid="stTabs"] [role="tabpanel"] {
  padding: 0 !important;
}

/* ── Dataframes ──────────────────────────────────────── */
[data-testid="stDataFrame"] {
  border: 1px solid var(--border) !important;
  border-radius: var(--r) !important;
  overflow: hidden !important;
  background: var(--bg-card) !important;
}
[data-testid="stDataFrame"] th {
  background: #0d1117 !important;
  color: var(--cyan) !important;
  font-family: var(--font-mono) !important;
  font-size: 0.75rem !important;
  letter-spacing: 1px !important;
  text-transform: uppercase !important;
}
[data-testid="stDataFrame"] td {
  font-family: var(--font-mono) !important;
  font-size: 0.8rem !important;
  color: var(--text-dim) !important;
  border-color: var(--border) !important;
}

/* ── st.metric cards ─────────────────────────────────── */
[data-testid="metric-container"] {
  background: var(--bg-card) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--r) !important;
  padding: 16px 20px !important;
  transition: border-color 0.3s ease, box-shadow 0.3s ease !important;
}
[data-testid="metric-container"]:hover {
  border-color: rgba(0,229,255,0.4) !important;
  box-shadow: 0 0 20px rgba(0,229,255,0.08) !important;
}
[data-testid="metric-container"] label {
  font-family: var(--font-mono) !important;
  font-size: 0.7rem !important;
  color: var(--text-muted) !important;
  letter-spacing: 1.5px !important;
  text-transform: uppercase !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
  font-family: var(--font-display) !important;
  font-size: 1.8rem !important;
  font-weight: 700 !important;
  color: var(--cyan) !important;
}

/* ── JSON viewer ─────────────────────────────────────── */
[data-testid="stJson"] {
  background: #060a10 !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--r) !important;
  font-family: var(--font-mono) !important;
  font-size: 0.78rem !important;
}

/* ── Text inputs ─────────────────────────────────────── */
.stTextInput input {
  background: var(--bg-card) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--r) !important;
  color: var(--text) !important;
  font-family: var(--font-mono) !important;
  font-size: 0.85rem !important;
}
.stTextInput input:focus {
  border-color: var(--purple) !important;
  box-shadow: 0 0 0 2px rgba(168,85,247,0.15) !important;
}

/* ── st.status / st.expander ─────────────────────────── */
[data-testid="stExpander"] {
  background: var(--bg-card) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--r) !important;
  overflow: hidden !important;
}
[data-testid="stExpander"] summary {
  font-family: var(--font-body) !important;
  color: var(--text-dim) !important;
  padding: 12px 16px !important;
}

/* ── Alerts ──────────────────────────────────────────── */
[data-testid="stAlert"] {
  border-radius: var(--r) !important;
  border: none !important;
  font-family: var(--font-body) !important;
}

/* ── Plotly charts ───────────────────────────────────── */
.js-plotly-plot {
  border-radius: var(--r) !important;
  overflow: hidden !important;
}

/* ── Annotated text ──────────────────────────────────── */
.fst-annotated-text span {
  font-family: var(--font-body) !important;
  font-size: 0.9rem !important;
  line-height: 1.9 !important;
}

/* ── CADIS Custom Components ─────────────────────────── */

/* Floating glass card */
.glass-card {
  background: linear-gradient(145deg, rgba(17,24,39,0.9), rgba(13,17,23,0.95));
  border: 1px solid var(--border);
  border-radius: var(--r-lg);
  padding: 24px 28px;
  margin: 12px 0;
  backdrop-filter: blur(12px);
  transition: border-color 0.3s ease, box-shadow 0.3s ease, transform 0.2s ease;
}
.glass-card:hover {
  border-color: rgba(0,229,255,0.25);
  box-shadow: 0 8px 32px rgba(0,229,255,0.06), 0 0 0 1px rgba(0,229,255,0.08);
  transform: translateY(-2px);
}
.glass-card.purple-glow:hover {
  border-color: rgba(168,85,247,0.35);
  box-shadow: 0 8px 32px rgba(168,85,247,0.1);
}
.glass-card.amber-glow:hover {
  border-color: rgba(245,158,11,0.35);
  box-shadow: 0 8px 32px rgba(245,158,11,0.1);
}

/* Module header */
.module-header {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 24px;
  padding-bottom: 20px;
  border-bottom: 1px solid var(--border);
}
.module-icon {
  width: 48px; height: 48px;
  border-radius: 14px;
  display: flex; align-items: center; justify-content: center;
  font-size: 1.4rem;
  flex-shrink: 0;
}
.icon-cyan   { background: rgba(0,229,255,0.1);  border: 1px solid rgba(0,229,255,0.2); }
.icon-purple { background: rgba(168,85,247,0.1); border: 1px solid rgba(168,85,247,0.2); }
.icon-amber  { background: rgba(245,158,11,0.1); border: 1px solid rgba(245,158,11,0.2); }
.icon-green  { background: rgba(16,185,129,0.1); border: 1px solid rgba(16,185,129,0.2); }
.icon-blue   { background: rgba(59,130,246,0.1); border: 1px solid rgba(59,130,246,0.2); }
.module-header-text h2 {
  margin: 0; padding: 0;
  font-family: var(--font-display) !important;
  font-size: 1.35rem !important;
  font-weight: 700 !important;
  color: var(--text) !important;
  letter-spacing: 0.5px;
}
.module-header-text p {
  margin: 4px 0 0; padding: 0;
  font-family: var(--font-mono) !important;
  font-size: 0.72rem !important;
  color: var(--text-muted) !important;
  letter-spacing: 0.8px;
}

/* Section label */
.section-label {
  font-family: var(--font-mono) !important;
  font-size: 0.68rem !important;
  letter-spacing: 2.5px !important;
  text-transform: uppercase !important;
  color: var(--text-muted) !important;
  margin: 24px 0 10px !important;
  display: flex;
  align-items: center;
  gap: 10px;
}
.section-label::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--border);
}

/* Token chip */
.token-stream {
  display: flex; flex-wrap: wrap; gap: 6px;
  padding: 16px;
  background: #060a10;
  border: 1px solid var(--border);
  border-radius: var(--r);
  font-family: var(--font-mono);
  line-height: 1.6;
}
.token-chip {
  display: inline-flex; align-items: center;
  padding: 3px 10px;
  border-radius: 6px;
  font-size: 0.78rem;
  font-family: var(--font-mono);
  transition: transform 0.15s ease;
}
.token-chip:hover { transform: translateY(-2px); }
.chip-noun   { background: rgba(0,229,255,0.08);  border: 1px solid rgba(0,229,255,0.2);  color: #00e5ff; }
.chip-verb   { background: rgba(168,85,247,0.08); border: 1px solid rgba(168,85,247,0.2); color: #a855f7; }
.chip-adj    { background: rgba(16,185,129,0.08); border: 1px solid rgba(16,185,129,0.2); color: #10b981; }
.chip-prop   { background: rgba(245,158,11,0.08); border: 1px solid rgba(245,158,11,0.2); color: #f59e0b; }
.chip-stop   { background: rgba(30,45,64,0.5);    border: 1px dashed #1e2d40;             color: #475569; }
.chip-other  { background: rgba(20,28,40,0.8);    border: 1px solid #1e2d40;              color: #64748b; }

/* Entity badge */
.ent-badge {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 5px 12px;
  border-radius: 8px;
  margin: 3px;
  font-family: var(--font-body);
  font-size: 0.82rem;
  font-weight: 500;
  cursor: default;
  transition: transform 0.15s ease, box-shadow 0.2s ease;
}
.ent-badge:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.4); }
.ent-badge .dot { width: 6px; height: 6px; border-radius: 50%; }

/* Relation row */
.relation-row {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 14px;
  background: #0a0f1e;
  border: 1px solid var(--border);
  border-radius: 10px;
  margin: 6px 0;
  font-family: var(--font-mono);
  font-size: 0.82rem;
  transition: border-color 0.2s ease;
}
.relation-row:hover { border-color: rgba(0,229,255,0.2); }
.rel-subj { color: var(--amber); font-weight: 600; }
.rel-verb { color: var(--purple); font-style: italic; padding: 2px 8px; background: rgba(168,85,247,0.08); border-radius: 4px; }
.rel-obj  { color: var(--cyan);  font-weight: 600; }
.rel-arrow { color: var(--text-muted); }

/* Ambiguity card */
.amb-wrapper {
  background: linear-gradient(135deg, rgba(245,158,11,0.04), rgba(17,24,39,0.9));
  border: 1px solid rgba(245,158,11,0.2);
  border-radius: var(--r-lg);
  padding: 20px 24px;
  margin: 12px 0;
  position: relative;
  overflow: hidden;
}
.amb-wrapper::before {
  content: '';
  position: absolute;
  top: 0; left: 0;
  width: 3px; height: 100%;
  background: linear-gradient(180deg, var(--amber), transparent);
}
.amb-type-pill {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 4px 12px;
  border-radius: 50px;
  font-family: var(--font-mono);
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 1px;
  text-transform: uppercase;
  background: rgba(245,158,11,0.1);
  border: 1px solid rgba(245,158,11,0.3);
  color: var(--amber);
  margin-bottom: 10px;
}
.amb-sentence {
  color: var(--text-dim);
  font-size: 0.9rem;
  line-height: 1.6;
  font-style: italic;
  margin: 8px 0;
  padding: 10px 14px;
  background: rgba(0,0,0,0.2);
  border-radius: 8px;
  border-left: 2px solid rgba(245,158,11,0.3);
}
.amb-description {
  color: var(--text-dim);
  font-size: 0.85rem;
  margin: 10px 0;
}
.resolution-card {
  background: linear-gradient(135deg, rgba(16,185,129,0.06), rgba(0,229,255,0.04));
  border: 1px solid rgba(16,185,129,0.25);
  border-radius: 10px;
  padding: 12px 16px;
  margin-top: 12px;
  display: flex; align-items: center; gap: 12px;
}
.resolution-icon { font-size: 1.2rem; }
.resolution-text { flex: 1; }
.resolution-text .label { font-family: var(--font-mono); font-size: 0.68rem; color: var(--text-muted); letter-spacing: 1.5px; text-transform: uppercase; margin-bottom: 2px; }
.resolution-text .value { font-family: var(--font-display); font-size: 1.05rem; font-weight: 600; color: var(--green); }
.conf-bar-bg { flex: 1; height: 4px; background: var(--border); border-radius: 2px; overflow: hidden; }
.conf-bar-fill { height: 100%; border-radius: 2px; background: linear-gradient(90deg, #10b981, #00e5ff); transition: width 0.6s ease; }

/* QA answer card */
.qa-answer-card {
  background: linear-gradient(135deg, rgba(0,229,255,0.04), rgba(59,130,246,0.06));
  border: 1px solid rgba(0,229,255,0.2);
  border-radius: var(--r-lg);
  padding: 24px 28px;
  margin: 16px 0;
  position: relative;
  overflow: hidden;
}
.qa-answer-card::after {
  content: '';
  position: absolute;
  bottom: -30px; right: -30px;
  width: 100px; height: 100px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(0,229,255,0.08), transparent);
  pointer-events: none;
}
.qa-question {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 1.5px;
  margin-bottom: 10px;
}
.qa-answer-text {
  font-family: var(--font-display);
  font-size: 1.6rem;
  font-weight: 700;
  color: #fff;
  margin: 0 0 14px;
  line-height: 1.3;
}
.qa-meta {
  display: flex; align-items: center; gap: 16px;
  flex-wrap: wrap;
}
.qa-meta-chip {
  display: flex; align-items: center; gap: 6px;
  padding: 4px 12px;
  border-radius: 50px;
  font-family: var(--font-mono);
  font-size: 0.72rem;
  background: rgba(255,255,255,0.04);
  border: 1px solid var(--border);
  color: var(--text-muted);
}
.conf-indicator { display: flex; align-items: center; gap: 8px; }
.conf-dot { width: 8px; height: 8px; border-radius: 50%; }
.conf-high   { background: var(--green); box-shadow: 0 0 6px var(--green); }
.conf-medium { background: var(--amber); box-shadow: 0 0 6px var(--amber); }
.conf-low    { background: var(--red);   box-shadow: 0 0 6px var(--red); }

/* Context highlight */
.qa-context {
  background: #060a10;
  border: 1px solid var(--border);
  border-radius: var(--r);
  padding: 16px 20px;
  font-family: var(--font-mono);
  font-size: 0.8rem;
  color: var(--text-muted);
  line-height: 1.8;
  margin-top: 12px;
}
.qa-highlight {
  background: rgba(0,229,255,0.12);
  border: 1px solid rgba(0,229,255,0.35);
  border-radius: 4px;
  color: var(--cyan);
  font-weight: 600;
  padding: 1px 4px;
}

/* Semantic search bubble */
.search-bubble {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 14px 14px 14px 4px;
  padding: 14px 18px;
  margin: 8px 0;
  transition: all 0.25s ease;
  position: relative;
  overflow: hidden;
}
.search-bubble:hover {
  border-color: rgba(0,229,255,0.25);
  transform: translateX(4px);
}
.search-bubble::before {
  content: '';
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 3px;
}
.bubble-rank-1::before { background: var(--cyan); }
.bubble-rank-2::before { background: var(--purple); }
.bubble-rank-3::before { background: var(--amber); }
.bubble-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 8px;
}
.bubble-rank {
  font-family: var(--font-mono);
  font-size: 0.68rem;
  color: var(--text-muted);
  letter-spacing: 1px;
  text-transform: uppercase;
}
.bubble-score {
  font-family: var(--font-mono);
  font-size: 0.78rem;
  font-weight: 600;
}
.bubble-text {
  color: var(--text-dim);
  font-size: 0.87rem;
  line-height: 1.55;
  margin-bottom: 10px;
}
.score-bar-bg { width: 100%; height: 3px; background: var(--border); border-radius: 2px; overflow: hidden; }
.score-bar-fill { height: 100%; border-radius: 2px; transition: width 0.8s ease; }
.bar-cyan   { background: linear-gradient(90deg, var(--cyan), #0070ff); }
.bar-purple { background: linear-gradient(90deg, var(--purple), #ff6b9d); }
.bar-amber  { background: linear-gradient(90deg, var(--amber), #ef4444); }

/* Summary executive card */
.exec-summary-card {
  background: linear-gradient(145deg, #0d1117, #111827);
  border: 1px solid var(--border);
  border-radius: var(--r-lg);
  padding: 28px;
  position: relative;
  overflow: hidden;
}
.exec-summary-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 2px;
  background: linear-gradient(90deg, var(--cyan), var(--purple), transparent);
}
.exec-label {
  font-family: var(--font-mono);
  font-size: 0.68rem;
  color: var(--text-muted);
  letter-spacing: 2px;
  text-transform: uppercase;
  margin-bottom: 14px;
  display: flex; align-items: center; gap: 8px;
}
.exec-label::before { content: ''; width: 6px; height: 6px; border-radius: 50%; background: var(--cyan); }
.exec-text {
  font-family: var(--font-body);
  font-size: 1.02rem;
  line-height: 1.75;
  color: var(--text);
}
.bullet-item {
  display: flex; align-items: flex-start; gap: 10px;
  padding: 10px 0;
  border-bottom: 1px solid rgba(30,45,64,0.5);
  font-size: 0.88rem;
  color: var(--text-dim);
  line-height: 1.55;
}
.bullet-dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: var(--purple);
  margin-top: 8px;
  flex-shrink: 0;
}

/* Timeline item */
.tl-item {
  display: flex; gap: 16px;
  margin: 0 0 16px;
  position: relative;
}
.tl-item::before {
  content: '';
  position: absolute;
  left: 38px; top: 32px;
  width: 1px;
  height: calc(100% + 8px);
  background: linear-gradient(180deg, rgba(0,229,255,0.3), transparent);
}
.tl-time-box {
  min-width: 76px;
  background: rgba(0,229,255,0.06);
  border: 1px solid rgba(0,229,255,0.15);
  border-radius: 8px;
  padding: 6px 8px;
  text-align: center;
  font-family: var(--font-mono);
  font-size: 0.72rem;
  color: var(--cyan);
  font-weight: 600;
  line-height: 1.3;
  flex-shrink: 0;
  align-self: flex-start;
}
.tl-content {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--r);
  padding: 12px 16px;
  font-size: 0.85rem;
  color: var(--text-dim);
  line-height: 1.5;
  flex: 1;
}

/* Compression stat card */
.stat-card {
  background: var(--bg-card2);
  border: 1px solid var(--border);
  border-radius: var(--r);
  padding: 18px 20px;
  text-align: center;
  transition: all 0.25s ease;
}
.stat-card:hover { border-color: rgba(168,85,247,0.3); box-shadow: 0 0 20px rgba(168,85,247,0.06); }
.stat-card .sv { font-family: var(--font-display); font-size: 2rem; font-weight: 800; color: var(--purple); }
.stat-card .sk { font-family: var(--font-mono); font-size: 0.65rem; color: var(--text-muted); letter-spacing: 1.5px; text-transform: uppercase; margin-top: 4px; }

/* Completion banner */
.completion-banner {
  background: linear-gradient(135deg, rgba(16,185,129,0.08), rgba(0,229,255,0.06));
  border: 1px solid rgba(16,185,129,0.3);
  border-radius: var(--r-lg);
  padding: 20px 24px;
  display: flex; align-items: center; gap: 16px;
  margin-top: 24px;
}
.comp-icon { font-size: 2rem; }
.comp-text h4 { margin: 0 0 4px; font-family: var(--font-display); font-size: 1rem; font-weight: 700; color: var(--green); }
.comp-text p  { margin: 0; font-size: 0.83rem; color: var(--text-muted); font-family: var(--font-mono); }

/* Welcome screen */
.welcome-hero {
  text-align: center;
  padding: 80px 20px 40px;
}
.welcome-hero h1 {
  font-family: var(--font-display) !important;
  font-size: 3.5rem !important;
  font-weight: 800 !important;
  background: linear-gradient(135deg, #00e5ff, #a855f7, #f59e0b) !important;
  -webkit-background-clip: text !important;
  -webkit-text-fill-color: transparent !important;
  background-clip: text !important;
  margin-bottom: 16px !important;
  letter-spacing: -1px !important;
  animation: shimmer 4s ease-in-out infinite;
  background-size: 200% auto;
}
@keyframes shimmer {
  0%   { background-position: 0% 50%; }
  50%  { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}
.welcome-hero p {
  color: var(--text-muted);
  font-size: 1rem;
  font-family: var(--font-mono) !important;
  letter-spacing: 0.5px;
}
.pipeline-flow {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-wrap: wrap;
  gap: 0;
  margin: 40px 0;
}
.pf-node {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 12px 16px;
  text-align: center;
  transition: all 0.3s ease;
  min-width: 110px;
  animation: fadeup 0.5s ease forwards;
  opacity: 0;
}
.pf-node:hover {
  border-color: rgba(0,229,255,0.3);
  box-shadow: 0 0 20px rgba(0,229,255,0.08);
  transform: translateY(-4px);
}
.pf-node:nth-child(1)  { animation-delay: 0.1s; }
.pf-node:nth-child(3)  { animation-delay: 0.2s; }
.pf-node:nth-child(5)  { animation-delay: 0.3s; }
.pf-node:nth-child(7)  { animation-delay: 0.4s; }
.pf-node:nth-child(9)  { animation-delay: 0.5s; }
.pf-node:nth-child(11) { animation-delay: 0.6s; }
@keyframes fadeup {
  from { opacity: 0; transform: translateY(14px); }
  to   { opacity: 1; transform: translateY(0); }
}
.pf-arrow { color: var(--border); font-size: 1.2rem; margin: 0 2px; padding-top: 6px; }
.pf-icon  { font-size: 1.4rem; display: block; margin-bottom: 6px; }
.pf-name  { font-family: var(--font-mono); font-size: 0.68rem; color: var(--text-muted); letter-spacing: 0.5px; }

/* Architecture sidebar */
.arch-step {
  display: flex; gap: 12px; align-items: flex-start;
  margin: 8px 0;
  padding: 8px 10px;
  border-radius: 8px;
  transition: background 0.2s;
}
.arch-step:hover { background: rgba(255,255,255,0.02); }
.arch-step-num {
  width: 22px; height: 22px;
  border-radius: 6px;
  display: flex; align-items: center; justify-content: center;
  font-family: var(--font-mono);
  font-size: 0.68rem;
  font-weight: 700;
  flex-shrink: 0;
  margin-top: 1px;
}
.arch-step-text { font-size: 0.78rem; color: var(--text-dim); line-height: 1.4; }
.arch-step-text span { font-family: var(--font-mono); font-size: 0.7rem; color: var(--text-muted); display: block; }

/* Info strip */
.info-strip {
  display: flex; align-items: center; gap: 10px;
  background: rgba(16,185,129,0.05);
  border: 1px solid rgba(16,185,129,0.15);
  border-radius: 10px;
  padding: 12px 16px;
  margin-top: 24px;
  font-size: 0.83rem;
  color: var(--text-muted);
  font-family: var(--font-mono);
}
.info-strip .icon { font-size: 1rem; }
</style>
"""

# ═══════════════════════════════════════════════════════════════
#  INJECT FUNCTION
# ═══════════════════════════════════════════════════════════════
def inject_css():
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
#  COMPONENT BUILDERS
# ═══════════════════════════════════════════════════════════════

def module_header(icon: str, icon_class: str, title: str, subtitle: str):
    st.markdown(f"""
    <div class="module-header">
      <div class="module-icon {icon_class}">{icon}</div>
      <div class="module-header-text">
        <h2>{title}</h2>
        <p>{subtitle}</p>
      </div>
    </div>
    """, unsafe_allow_html=True)

def section_label(text: str):
    st.markdown(f'<div class="section-label">{text}</div>', unsafe_allow_html=True)

def token_stream(tokens_with_pos: list):
    """tokens_with_pos: list of (text, pos_) tuples"""
    css_map = {
        "NOUN": "chip-noun", "PROPN": "chip-prop",
        "VERB": "chip-verb", "AUX":  "chip-verb",
        "ADJ":  "chip-adj",  "ADV":  "chip-adj",
    }
    chips = ""
    for text, pos, is_stop in tokens_with_pos:
        if is_stop:
            cls = "chip-stop"
        else:
            cls = css_map.get(pos, "chip-other")
        chips += f'<span class="token-chip {cls}" title="{pos}">{text}</span>'
    st.markdown(f'<div class="token-stream">{chips}</div>', unsafe_allow_html=True)

def entity_badge(text: str, label: str):
    fg, bg = ENTITY_COLORS.get(label, ("#64748b", "#0d1117"))
    dot_color = fg
    return (
        f'<span class="ent-badge" '
        f'style="background:{bg};border:1px solid {fg}40;color:{fg}" '
        f'title="{label}">'
        f'<span class="dot" style="background:{dot_color}"></span>'
        f'{text}'
        f'</span>'
    )

def render_entities(entities: dict):
    html = ""
    for label, ents in entities.items():
        if not ents:
            continue
        badges = "".join(entity_badge(e["text"], label) for e in ents)
        fg = ENTITY_COLORS.get(label, ("#64748b", "#0d1117"))[0]
        html += f"""
        <div style="margin:10px 0;">
          <span style="font-family:var(--font-mono);font-size:0.68rem;
                       color:{fg};letter-spacing:2px;text-transform:uppercase;
                       margin-right:10px;">{label}</span>
          {badges}
        </div>"""
    st.markdown(html, unsafe_allow_html=True)

def relation_row(subj: str, verb: str, obj: str):
    return f"""
    <div class="relation-row">
      <span class="rel-subj">{subj}</span>
      <span class="rel-arrow">→</span>
      <span class="rel-verb">{verb}</span>
      <span class="rel-arrow">→</span>
      <span class="rel-obj">{obj}</span>
    </div>"""

def ambiguity_card(a: dict, idx: int):
    conf = a["confidence"]
    bar_pct = int(conf * 100)
    html = f"""
    <div class="amb-wrapper">
      <div class="amb-type-pill">{a['emoji']} {a['type']}</div>
      <div class="amb-sentence">"{a['sentence']}"</div>
      <div class="amb-description">{a['description']}</div>
      <div class="resolution-card">
        <div class="resolution-icon">✅</div>
        <div class="resolution-text">
          <div class="label">Resolved to</div>
          <div class="value">{a['resolved']}</div>
        </div>
        <div style="text-align:right">
          <div style="font-family:var(--font-mono);font-size:0.68rem;color:var(--text-muted);margin-bottom:4px">CONFIDENCE</div>
          <div style="font-family:var(--font-display);font-size:1.1rem;font-weight:700;color:var(--green)">{conf:.0%}</div>
          <div class="conf-bar-bg" style="width:80px;margin-top:4px">
            <div class="conf-bar-fill" style="width:{bar_pct}%"></div>
          </div>
        </div>
      </div>
    </div>"""
    st.markdown(html, unsafe_allow_html=True)

def search_bubble(rank: int, sentence: str, score: float):
    rank_cls   = f"bubble-rank-{min(rank, 3)}"
    bar_cls    = ["bar-cyan", "bar-purple", "bar-amber"][min(rank - 1, 2)]
    score_color = "#00e5ff" if score > 0.45 else "#f59e0b" if score > 0.25 else "#ef4444"
    bar_pct    = int(score * 100)
    st.markdown(f"""
    <div class="search-bubble {rank_cls}">
      <div class="bubble-header">
        <span class="bubble-rank">Match #{rank}</span>
        <span class="bubble-score" style="color:{score_color}">{score:.3f}</span>
      </div>
      <div class="bubble-text">{sentence}</div>
      <div class="score-bar-bg">
        <div class="score-bar-fill {bar_cls}" style="width:{bar_pct}%"></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

def qa_answer_card(question: str, answer: str, score: float, start: int, end: int):
    conf_cls   = "conf-high" if score > 0.5 else "conf-medium" if score > 0.2 else "conf-low"
    conf_label = "High"      if score > 0.5 else "Medium"       if score > 0.2 else "Low"
    st.markdown(f"""
    <div class="qa-answer-card">
      <div class="qa-question">Answer</div>
      <div class="qa-answer-text">{answer}</div>
      <div class="qa-meta">
        <div class="conf-indicator">
          <div class="conf-dot {conf_cls}"></div>
          <span style="font-family:var(--font-mono);font-size:0.75rem;color:var(--text-muted)">
            {conf_label} confidence — {score:.1%}
          </span>
        </div>
        <div class="qa-meta-chip">📍 chars {start}–{end}</div>
        <div class="qa-meta-chip">⚡ RoBERTa · SQuAD 2.0</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

def qa_context_highlight(doc_text: str, start: int, end: int):
    s = max(0, start - 120)
    e = min(len(doc_text), end + 120)
    before = doc_text[s:start]
    answer = doc_text[start:end]
    after  = doc_text[end:e]
    st.markdown(f"""
    <div class="qa-context">
      {"…" if s > 0 else ""}{before}<span class="qa-highlight">{answer}</span>{after}{"…" if e < len(doc_text) else ""}
    </div>
    """, unsafe_allow_html=True)

def exec_summary_card(text: str):
    st.markdown(f"""
    <div class="exec-summary-card">
      <div class="exec-label">Executive Summary · DistilBART Abstractive</div>
      <div class="exec-text">{text}</div>
    </div>
    """, unsafe_allow_html=True)

def bullet_summary(sentences: list):
    items = "".join(
        f'<div class="bullet-item"><div class="bullet-dot"></div><div>{s}</div></div>'
        for s in sentences
    )
    st.markdown(f"""
    <div class="glass-card purple-glow">
      <div class="exec-label">Key Sentences · Entity-Density Extraction</div>
      {items}
    </div>
    """, unsafe_allow_html=True)

def timeline_item(time_str: str, event_text: str):
    return f"""
    <div class="tl-item">
      <div class="tl-time-box">{time_str}</div>
      <div class="tl-content">{event_text}</div>
    </div>"""

def stat_cards(stats: list):
    """stats: list of (value, key) tuples"""
    cols = st.columns(len(stats))
    for i, (val, key) in enumerate(stats):
        cols[i].markdown(f"""
        <div class="stat-card">
          <div class="sv">{val}</div>
          <div class="sk">{key}</div>
        </div>
        """, unsafe_allow_html=True)

def info_strip(text: str):
    st.markdown(f"""
    <div class="info-strip">
      <span class="icon">✅</span>
      {text}
    </div>
    """, unsafe_allow_html=True)

def completion_banner(modules: int = 6):
    st.markdown(f"""
    <div class="completion-banner">
      <div class="comp-icon">🎯</div>
      <div class="comp-text">
        <h4>Full CADIS Pipeline Complete</h4>
        <p>All {modules} modules executed · Results ready for research presentation</p>
      </div>
    </div>
    """, unsafe_allow_html=True)

def welcome_screen():
    pipeline = [
        ("📝", "Preprocessing"),
        ("🔢", "Embeddings"),
        ("🏷️", "NER + IE"),
        ("🔀", "Ambiguity"),
        ("❓", "QA Engine"),
        ("📋", "Summary"),
    ]
    nodes = ""
    for i, (icon, name) in enumerate(pipeline):
        nodes += f'<div class="pf-node"><span class="pf-icon">{icon}</span><div class="pf-name">{name}</div></div>'
        if i < len(pipeline) - 1:
            nodes += '<div class="pf-arrow">→</div>'

    st.markdown(f"""
    <div class="welcome-hero">
      <h1>CADIS</h1>
      <p>Context-Aware Document Intelligence System &nbsp;·&nbsp; 6-Module NLP Research Pipeline</p>
      <div class="pipeline-flow">{nodes}</div>
      <p style="color:var(--text-muted);font-size:0.85rem">
        ← Paste a document in the sidebar and click <strong style="color:var(--cyan)">RUN PIPELINE</strong>
      </p>
    </div>
    """, unsafe_allow_html=True)

def sidebar_architecture():
    steps = [
        ("#00e5ff", "1", "Preprocessing", "Tokenization · POS · Normalization"),
        ("#a855f7", "2", "Embeddings",    "MiniLM-L6-v2 · Cosine Similarity"),
        ("#f59e0b", "3", "NER + IE",      "BERT-NER · SVO Extraction"),
        ("#ef4444", "4", "Ambiguity",     "PP-Attach · Anaphora · Semantic"),
        ("#10b981", "5", "QA Engine",     "RoBERTa · SQuAD 2.0"),
        ("#3b82f6", "6", "Summary",       "DistilBART · Timeline · Bullets"),
    ]
    html = '<div style="margin-top:8px">'
    for color, num, name, detail in steps:
        html += f"""
        <div class="arch-step">
          <div class="arch-step-num" style="background:{color}15;border:1px solid {color}40;color:{color}">{num}</div>
          <div class="arch-step-text">{name}<span>{detail}</span></div>
        </div>"""
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)

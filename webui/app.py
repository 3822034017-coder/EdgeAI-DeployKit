import json
import os
import shutil
import subprocess
import time
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


PROJECT_ROOT = Path(__file__).resolve().parents[1]
HOME = Path.home()
OUTPUTS_DIR = Path(os.environ.get("EDGEAI_OUTPUTS", HOME / "edgeai-outputs"))
REPORTS_DIR = Path(os.environ.get("EDGEAI_REPORTS", HOME / "edgeai-reports"))
PACKAGES_DIR = OUTPUTS_DIR / "packages"
MATRIX_JSON = OUTPUTS_DIR / "model_matrix" / "matrix.json"

# ═══════════════════════════════════════════
#  Tech Theme CSS
# ═══════════════════════════════════════════

TECH_CSS = """
<style>
/* ── base ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

* { font-family: 'Inter', 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif; }

body, .stApp {
    background: linear-gradient(135deg, #0a0e17 0%, #111827 50%, #0f172a 100%);
    color: #e2e8f0;
}

/* ── sidebar ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d1321 0%, #111827 100%);
    border-right: 1px solid #1e293b;
}
[data-testid="stSidebar"] * { color: #cbd5e1; }
[data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 { color: #38bdf8; }

/* ── header gradient ── */
.tech-header {
    background: linear-gradient(135deg, #06b6d4 0%, #3b82f6 50%, #8b5cf6 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    font-size: 2.4rem;
    font-weight: 700;
    letter-spacing: -0.02em;
    margin-bottom: 0.3rem;
}
.tech-subtitle {
    color: #64748b;
    font-size: 0.95rem;
    font-weight: 400;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}

/* ── clock ── */
.tech-clock {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: rgba(6, 182, 212, 0.08);
    border: 1px solid rgba(6, 182, 212, 0.25);
    border-radius: 8px;
    padding: 8px 16px;
    font-family: 'SF Mono', 'Cascadia Code', 'Consolas', monospace;
    font-size: 0.9rem;
    color: #38bdf8;
    letter-spacing: 0.05em;
}
.tech-clock-dot {
    width: 8px; height: 8px;
    background: #22d3ee;
    border-radius: 50%;
    animation: pulse-dot 2s ease-in-out infinite;
    box-shadow: 0 0 8px #22d3ee;
}
@keyframes pulse-dot {
    0%, 100% { opacity: 1; box-shadow: 0 0 8px #22d3ee; }
    50% { opacity: 0.4; box-shadow: 0 0 2px #22d3ee; }
}

/* ── cards ── */
.tech-card {
    background: rgba(15, 23, 42, 0.7);
    border: 1px solid rgba(56, 189, 248, 0.12);
    border-radius: 12px;
    padding: 20px 24px;
    margin: 12px 0;
    backdrop-filter: blur(10px);
    transition: border-color 0.3s;
}
.tech-card:hover { border-color: rgba(56, 189, 248, 0.35); }
.tech-card h3 { color: #38bdf8; margin-top: 0; font-size: 1.1rem; }

/* ── metric box ── */
.tech-metric {
    background: rgba(6, 182, 212, 0.06);
    border: 1px solid rgba(6, 182, 212, 0.15);
    border-radius: 10px;
    padding: 14px 18px;
    text-align: center;
}
.tech-metric-label {
    font-size: 0.75rem;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}
.tech-metric-value {
    font-size: 1.5rem;
    font-weight: 700;
    color: #38bdf8;
    font-family: 'SF Mono', 'Cascadia Code', 'Consolas', monospace;
}

/* ── status badges ── */
.badge-pass { color: #22d3ee; }
.badge-fail { color: #f87171; }
.badge-pending { color: #94a3b8; }

/* ── buttons ── */
.stButton > button {
    background: linear-gradient(135deg, rgba(6,182,212,0.12) 0%, rgba(59,130,246,0.12) 100%) !important;
    border: 1px solid rgba(56,189,248,0.3) !important;
    color: #38bdf8 !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
    transition: all 0.25s !important;
}
.stButton > button:hover {
    background: linear-gradient(135deg, rgba(6,182,212,0.22) 0%, rgba(59,130,246,0.22) 100%) !important;
    border-color: #38bdf8 !important;
    box-shadow: 0 0 16px rgba(56,189,248,0.15) !important;
    transform: translateY(-1px);
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #06b6d4 0%, #3b82f6 100%) !important;
    border: none !important;
    color: #fff !important;
    font-weight: 600 !important;
}
.stButton > button[kind="primary"]:hover {
    box-shadow: 0 0 24px rgba(56,189,248,0.35) !important;
}

/* ── expander ── */
[data-testid="stExpander"] {
    background: rgba(15,23,42,0.5);
    border: 1px solid rgba(56,189,248,0.1);
    border-radius: 10px;
}
[data-testid="stExpander"] summary { color: #94a3b8; }

/* ── code blocks ── */
code, pre {
    background: rgba(2,6,23,0.8) !important;
    border: 1px solid rgba(56,189,248,0.12) !important;
    border-radius: 8px !important;
    color: #38bdf8 !important;
    font-family: 'SF Mono', 'Cascadia Code', 'Consolas', monospace !important;
}

/* ── tabs ── */
[data-testid="stTabs"] button {
    color: #94a3b8 !important;
    font-weight: 500 !important;
}
[data-testid="stTabs"] button[aria-selected="true"] {
    color: #38bdf8 !important;
    border-bottom: 2px solid #38bdf8 !important;
}

/* ── text inputs / selects ── */
[data-baseweb="input"], [data-baseweb="select"] {
    background: rgba(15,23,42,0.6) !important;
    border-color: rgba(56,189,248,0.2) !important;
    color: #e2e8f0 !important;
    border-radius: 8px !important;
}
[data-baseweb="input"]:focus, [data-baseweb="select"]:focus {
    border-color: #38bdf8 !important;
    box-shadow: 0 0 8px rgba(56,189,248,0.1) !important;
}

/* ── radio ── */
[data-testid="stRadio"] label { color: #cbd5e1; }

/* ── success / error / warning / info ── */
[data-testid="stSuccess"] { background: rgba(34,211,238,0.08); border: 1px solid rgba(34,211,238,0.2); border-radius: 8px; }
[data-testid="stError"]   { background: rgba(248,113,113,0.08); border: 1px solid rgba(248,113,113,0.2); border-radius: 8px; }
[data-testid="stWarning"] { background: rgba(251,191,36,0.08); border: 1px solid rgba(251,191,36,0.2); border-radius: 8px; }
[data-testid="stInfo"]    { background: rgba(148,163,184,0.06); border: 1px solid rgba(148,163,184,0.12); border-radius: 8px; }
</style>
"""

# ═══════════════════════════════════════════
#  Real-time clock component
# ═══════════════════════════════════════════

CLOCK_HTML = """
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body {
  background: transparent;
  min-height: 78px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: "SF Pro Display", "HarmonyOS Sans SC", "MiSans", "Segoe UI", "PingFang SC", system-ui, sans-serif;
}
.runtime-strip {
  width: min(860px, 96%);
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 18px;
  border-radius: 18px;
  color: #dfe8f4;
  background:
    linear-gradient(180deg, rgba(18, 24, 36, .76), rgba(8, 12, 20, .62));
  border: 1px solid rgba(169, 186, 208, .16);
  box-shadow:
    0 18px 50px rgba(0,0,0,.28),
    inset 0 1px 0 rgba(255,255,255,.045);
  backdrop-filter: blur(18px);
}
.runtime-left {
  display: inline-flex;
  align-items: center;
  gap: 11px;
  min-width: 0;
}
.runtime-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #7dd3fc;
  box-shadow: 0 0 0 6px rgba(125,211,252,.08), 0 0 18px rgba(125,211,252,.55);
  animation: pulse 2.8s ease-in-out infinite;
}
.runtime-title {
  font-size: 12px;
  letter-spacing: .16em;
  text-transform: uppercase;
  color: #9aa7ba;
  white-space: nowrap;
}
.runtime-time {
  font-family: "JetBrains Mono", "SF Mono", "Cascadia Code", Consolas, monospace;
  font-size: 13px;
  letter-spacing: .06em;
  color: #eef6ff;
  white-space: nowrap;
}
.runtime-line {
  flex: 1;
  height: 1px;
  margin: 0 18px;
  background: linear-gradient(90deg, transparent, rgba(125,211,252,.24), rgba(183,167,255,.18), transparent);
}
@keyframes pulse {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(.72); opacity: .55; }
}
</style>
<div class="runtime-strip">
  <div class="runtime-left">
    <span class="runtime-dot"></span>
    <span class="runtime-title">EDGE RUNTIME ONLINE</span>
  </div>
  <span class="runtime-line"></span>
  <span id="runtime-time" class="runtime-time">---- -- -- --:--:--</span>
</div>
<script>
(function tick() {
  var now = new Date();
  var str = now.getFullYear() + '-' +
    String(now.getMonth()+1).padStart(2,'0') + '-' +
    String(now.getDate()).padStart(2,'0') + '  ' +
    String(now.getHours()).padStart(2,'0') + ':' +
    String(now.getMinutes()).padStart(2,'0') + ':' +
    String(now.getSeconds()).padStart(2,'0');
  var el = document.getElementById('runtime-time');
  if (el) el.textContent = str;
  setTimeout(tick, 1000);
})();
</script>
"""

PREMIUM_CSS = """
<style>
/* ═══════════════════════════════════════════
   EdgeAI Premium Theme — Obsidian Console
   关键词：克制、高级、工程感、低饱和、少塑料感
   ═══════════════════════════════════════════ */
:root {
    --bg-0: #05070b;
    --bg-1: #090d15;
    --bg-2: #0d1320;
    --panel: rgba(15, 21, 32, .74);
    --panel-soft: rgba(18, 25, 38, .54);
    --panel-solid: #111827;
    --stroke: rgba(178, 196, 220, .13);
    --stroke-strong: rgba(136, 203, 255, .28);
    --text: #e8eef7;
    --text-soft: #c5d0df;
    --muted: #8793a6;
    --faint: #5f6f83;
    --accent: #7dd3fc;
    --accent-2: #b8a8ff;
    --ok: #7ce7b2;
    --warn: #f4c76b;
    --bad: #ff8a9a;
    --radius-lg: 18px;
    --radius-md: 14px;
    --shadow-card: 0 18px 42px rgba(0, 0, 0, .30);
    --shadow-soft: 0 10px 30px rgba(0, 0, 0, .20);
}

* {
    font-family: "SF Pro Display", "HarmonyOS Sans SC", "MiSans", "Segoe UI", "PingFang SC", "Microsoft YaHei", system-ui, -apple-system, sans-serif !important;
    -webkit-font-smoothing: antialiased;
    text-rendering: geometricPrecision;
}

html, body, .stApp {
    color: var(--text) !important;
    background:
      radial-gradient(circle at 18% 8%, rgba(72, 121, 255, .13), transparent 34%),
      radial-gradient(circle at 80% 4%, rgba(125, 211, 252, .10), transparent 30%),
      radial-gradient(circle at 68% 86%, rgba(184, 168, 255, .10), transparent 32%),
      linear-gradient(140deg, var(--bg-0) 0%, var(--bg-1) 46%, #070b12 100%) !important;
}

.stApp::before {
    content: "";
    position: fixed;
    inset: 0;
    pointer-events: none;
    z-index: -2;
    opacity: .42;
    background:
      linear-gradient(rgba(148, 163, 184, .055) 1px, transparent 1px),
      linear-gradient(90deg, rgba(148, 163, 184, .045) 1px, transparent 1px);
    background-size: 64px 64px;
    mask-image: radial-gradient(circle at 50% 18%, black 0%, transparent 78%);
}

.stApp::after {
    content: "";
    position: fixed;
    inset: 0;
    pointer-events: none;
    z-index: -1;
    opacity: .36;
    background-image:
      url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='180' height='180' viewBox='0 0 180 180'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.75' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='180' height='180' filter='url(%23n)' opacity='.20'/%3E%3C/svg%3E"),
      linear-gradient(118deg, transparent 0%, rgba(125, 211, 252, .045) 44%, transparent 62%);
    mix-blend-mode: screen;
}

.block-container {
    max-width: 1420px !important;
    padding-top: 1.15rem !important;
    padding-bottom: 3rem !important;
}

h1, h2, h3, h4, h5, h6 { color: var(--text) !important; letter-spacing: -.02em; }
p, li, label, span, div { color: inherit; }
.stCaptionContainer, .stMarkdown small, [data-testid="stMarkdownContainer"] p { color: var(--text-soft); }

a { color: var(--accent) !important; text-decoration-color: rgba(125,211,252,.32) !important; }
hr, .stDivider { border-color: rgba(178,196,220,.10) !important; }

/* Sidebar：低调的设备舱，不做亮面塑料 */
[data-testid="stSidebar"] {
    background:
      linear-gradient(180deg, rgba(7, 10, 16, .96), rgba(12, 17, 26, .92)) !important;
    border-right: 1px solid rgba(178,196,220,.11) !important;
    box-shadow: 24px 0 70px rgba(0,0,0,.30);
}
[data-testid="stSidebar"] * { color: #cbd5e1 !important; }
[data-testid="stSidebar"] .stCodeBlock,
[data-testid="stSidebar"] code {
    color: #a7ddff !important;
    background: rgba(0,0,0,.22) !important;
    border-color: rgba(178,196,220,.10) !important;
}

/* Header：从“海报感”改成“产品主控台” */
.edge-header {
    position: relative;
    overflow: hidden;
    border-radius: 24px;
    padding: 28px 32px 26px 32px;
    background:
      linear-gradient(180deg, rgba(17, 24, 39, .84), rgba(9, 13, 21, .70)),
      radial-gradient(circle at 84% 18%, rgba(125,211,252,.12), transparent 34%);
    border: 1px solid rgba(178,196,220,.15);
    box-shadow: var(--shadow-card), inset 0 1px 0 rgba(255,255,255,.045);
    backdrop-filter: blur(22px);
}
.edge-header::before {
    content: "";
    position: absolute;
    inset: 0 0 auto 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(125,211,252,.56), rgba(184,168,255,.32), transparent);
}
.edge-header::after {
    content: "";
    position: absolute;
    right: 26px;
    top: 22px;
    width: 360px;
    height: 160px;
    opacity: .32;
    background:
      linear-gradient(rgba(125,211,252,.20) 1px, transparent 1px),
      linear-gradient(90deg, rgba(125,211,252,.16) 1px, transparent 1px);
    background-size: 24px 24px;
    mask-image: linear-gradient(90deg, transparent 0%, black 34%, transparent 100%);
    transform: perspective(600px) rotateX(58deg) rotateZ(-3deg);
}
.edge-kicker {
    position: relative;
    z-index: 2;
    display: inline-flex;
    align-items: center;
    gap: 9px;
    color: var(--muted) !important;
    font-size: .74rem;
    line-height: 1;
    letter-spacing: .18em;
    text-transform: uppercase;
    margin-bottom: 14px;
}
.edge-kicker::before {
    content: "";
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--accent);
    box-shadow: 0 0 0 6px rgba(125,211,252,.08), 0 0 18px rgba(125,211,252,.36);
}
.edge-title {
    position: relative;
    z-index: 2;
    color: #f4f8ff !important;
    font-size: clamp(2.05rem, 3vw, 3rem);
    line-height: 1.04;
    font-weight: 760;
    letter-spacing: -.045em;
    margin: 0 0 12px 0;
    text-shadow: 0 1px 0 rgba(255,255,255,.04);
}
.edge-subtitle {
    position: relative;
    z-index: 2;
    max-width: 920px;
    color: #a9b6c8 !important;
    font-size: .98rem;
    line-height: 1.72;
}
.edge-tag-row {
    position: relative;
    z-index: 2;
    display: flex;
    flex-wrap: wrap;
    gap: 9px;
    margin-top: 18px;
}
.edge-tag {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 7px 11px;
    border-radius: 999px;
    color: #dbe7f5 !important;
    border: 1px solid rgba(178,196,220,.14);
    background: rgba(255,255,255,.035);
    box-shadow: inset 0 1px 0 rgba(255,255,255,.035);
    font-size: .78rem;
    letter-spacing: .025em;
    white-space: nowrap;
}
.edge-tag::before {
    content: "";
    width: 5px;
    height: 5px;
    border-radius: 50%;
    background: rgba(125,211,252,.75);
}

/* 卡片系统：减少高光和饱和色，统一间距 */
.edge-kpi, .edge-panel, .tech-card, [data-testid="stMetric"], [data-testid="stExpander"] {
    background: var(--panel) !important;
    border: 1px solid var(--stroke) !important;
    border-radius: var(--radius-lg) !important;
    box-shadow: var(--shadow-soft), inset 0 1px 0 rgba(255,255,255,.035) !important;
    backdrop-filter: blur(18px);
}
.edge-kpi {
    position: relative;
    overflow: hidden;
    min-height: 118px;
    padding: 17px 18px;
}
.edge-kpi::before {
    content: "";
    position: absolute;
    left: 0;
    top: 16px;
    bottom: 16px;
    width: 2px;
    border-radius: 999px;
    background: linear-gradient(180deg, rgba(125,211,252,.90), rgba(184,168,255,.42));
}
.edge-kpi.blue::before { background: linear-gradient(180deg, #93c5fd, rgba(125,211,252,.38)); }
.edge-kpi.green::before { background: linear-gradient(180deg, var(--ok), rgba(125,211,252,.28)); }
.edge-kpi.amber::before { background: linear-gradient(180deg, var(--warn), rgba(125,211,252,.25)); }
.edge-kpi.red::before { background: linear-gradient(180deg, var(--bad), rgba(125,211,252,.25)); }
.edge-kpi-label, .tech-metric-label {
    color: var(--muted) !important;
    font-size: .74rem;
    letter-spacing: .08em;
    text-transform: uppercase;
}
.edge-kpi-value, .tech-metric-value {
    color: #f5f9ff !important;
    font-size: 1.55rem;
    line-height: 1.2;
    font-weight: 740;
    margin-top: 8px;
    letter-spacing: -.035em;
}
.edge-kpi-note, .edge-panel-note, .step-note {
    color: var(--muted) !important;
    font-size: .78rem;
    line-height: 1.55;
}
.edge-panel, .tech-card { padding: 18px 20px; }
.edge-panel-title, .tech-card h3 {
    color: #f2f6fd !important;
    font-size: 1.02rem;
    font-weight: 720;
    margin-top: 0;
}
.tech-metric {
    background: var(--panel) !important;
    border: 1px solid var(--stroke) !important;
    border-radius: var(--radius-md) !important;
    padding: 15px 16px;
    text-align: left;
    box-shadow: var(--shadow-soft);
}

/* 流程步骤：像工程状态条，不像儿童卡片 */
.step-rail {
    display: grid;
    grid-template-columns: repeat(6, minmax(0, 1fr));
    gap: 12px;
}
.step-box {
    position: relative;
    overflow: hidden;
    min-height: 98px;
    padding: 13px 14px;
    border-radius: var(--radius-md);
    border: 1px solid rgba(178,196,220,.12);
    background: rgba(15, 21, 32, .55);
    box-shadow: 0 12px 28px rgba(0,0,0,.18), inset 0 1px 0 rgba(255,255,255,.026);
}
.step-box::before {
    content: "";
    position: absolute;
    left: 13px;
    top: 12px;
    width: 5px;
    height: 5px;
    border-radius: 50%;
    background: rgba(135,147,166,.70);
}
.step-box.done { border-color: rgba(124,231,178,.26); background: rgba(15, 42, 35, .42); }
.step-box.done::before { background: var(--ok); box-shadow: 0 0 14px rgba(124,231,178,.35); }
.step-box.wait { background: rgba(15, 21, 32, .46); }
.step-title { color: #edf4ff !important; font-weight: 700; font-size: .86rem; padding-left: 14px; }
.step-note { margin-top: 7px; }

.status-chip {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 999px;
    padding: 4px 9px;
    font-size: .68rem;
    line-height: 1;
    font-weight: 740;
    letter-spacing: .04em;
    border: 1px solid rgba(178,196,220,.13);
    background: rgba(255,255,255,.035);
    color: #aebacd !important;
    white-space: nowrap;
}
.status-pass { background: rgba(124,231,178,.10); border-color: rgba(124,231,178,.26); color: #a7f3d0 !important; }
.status-fail { background: rgba(255,138,154,.10); border-color: rgba(255,138,154,.24); color: #fecdd3 !important; }
.status-running { background: rgba(125,211,252,.10); border-color: rgba(125,211,252,.26); color: #bae6fd !important; }
.status-skip { background: rgba(244,199,107,.10); border-color: rgba(244,199,107,.26); color: #fde68a !important; }

/* Buttons：主按钮稳重，次按钮不发廉价光 */
.stButton > button {
    border-radius: 13px !important;
    border: 1px solid rgba(178,196,220,.16) !important;
    background: rgba(255,255,255,.045) !important;
    color: #edf4ff !important;
    font-weight: 650 !important;
    min-height: 2.55rem;
    box-shadow: inset 0 1px 0 rgba(255,255,255,.035);
    transition: transform .16s ease, border-color .16s ease, background .16s ease, box-shadow .16s ease !important;
}
.stButton > button:hover {
    transform: translateY(-1px);
    border-color: rgba(125,211,252,.40) !important;
    background: rgba(125,211,252,.075) !important;
    box-shadow: 0 12px 24px rgba(0,0,0,.22), inset 0 1px 0 rgba(255,255,255,.04) !important;
}
.stButton > button[kind="primary"] {
    border-color: rgba(125,211,252,.52) !important;
    background: linear-gradient(180deg, rgba(52, 122, 169, .92), rgba(21, 78, 112, .92)) !important;
    color: #ffffff !important;
    box-shadow: 0 12px 30px rgba(7, 89, 133, .22), inset 0 1px 0 rgba(255,255,255,.12) !important;
}

/* Tabs */
[data-testid="stTabs"] {
    background: rgba(5, 7, 11, .34);
    border: 1px solid rgba(178,196,220,.09);
    border-radius: 18px;
    padding: 8px 10px 0 10px;
    backdrop-filter: blur(16px);
}
[data-testid="stTabs"] button {
    color: #9aa7ba !important;
    font-weight: 650 !important;
    border-radius: 12px 12px 0 0 !important;
}
[data-testid="stTabs"] button[aria-selected="true"] {
    color: #f4f8ff !important;
    border-bottom: 2px solid rgba(125,211,252,.72) !important;
    background: rgba(255,255,255,.035) !important;
}

/* Forms / uploader */
[data-baseweb="input"], [data-baseweb="select"], textarea,
[data-testid="stTextInput"] input, [data-testid="stNumberInput"] input {
    background: rgba(5, 7, 11, .48) !important;
    border-color: rgba(178,196,220,.14) !important;
    color: #edf4ff !important;
    border-radius: 13px !important;
}
[data-baseweb="input"]:focus-within, [data-baseweb="select"]:focus-within,
[data-testid="stTextInput"] input:focus {
    border-color: rgba(125,211,252,.46) !important;
    box-shadow: 0 0 0 3px rgba(125,211,252,.08) !important;
}
[data-testid="stFileUploader"] section {
    background: rgba(5, 7, 11, .42) !important;
    border: 1px dashed rgba(178,196,220,.18) !important;
    border-radius: 16px !important;
}
[data-testid="stFileUploader"] * { color: #d8e3f2 !important; }

/* Tables / code */
[data-testid="stDataFrame"] {
    border: 1px solid rgba(178,196,220,.12);
    border-radius: 16px;
    overflow: hidden;
    box-shadow: var(--shadow-soft);
}
.cmd-preview, code, pre, .stCodeBlock {
    border: 1px solid rgba(178,196,220,.12) !important;
    border-radius: 14px !important;
    background: rgba(2, 4, 8, .68) !important;
    color: #d9f3ff !important;
    font-family: "JetBrains Mono", "SF Mono", "Cascadia Code", Consolas, monospace !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,.025);
}
.cmd-preview {
    padding: 11px 12px;
    font-size: .78rem;
    overflow-x: auto;
    white-space: pre-wrap;
}

/* Alerts */
[data-testid="stSuccess"] { background: rgba(124,231,178,.09) !important; border: 1px solid rgba(124,231,178,.20) !important; border-radius: 14px !important; }
[data-testid="stError"]   { background: rgba(255,138,154,.09) !important; border: 1px solid rgba(255,138,154,.20) !important; border-radius: 14px !important; }
[data-testid="stWarning"] { background: rgba(244,199,107,.09) !important; border: 1px solid rgba(244,199,107,.20) !important; border-radius: 14px !important; }
[data-testid="stInfo"]    { background: rgba(125,211,252,.075) !important; border: 1px solid rgba(125,211,252,.16) !important; border-radius: 14px !important; }

@media (max-width: 900px) {
    .step-rail { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .edge-header { padding: 22px 20px; border-radius: 20px; }
    .edge-title { font-size: 2rem; }
}
</style>
"""

# ═══════════════════════════════════════════
#  Basic helpers
# ═══════════════════════════════════════════

def ensure_dirs() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    PACKAGES_DIR.mkdir(parents=True, exist_ok=True)


def abs_path(path_text: str | Path) -> Path:
    p = Path(path_text)
    return p if p.is_absolute() else PROJECT_ROOT / p


def rel(path: str | Path) -> str:
    p = Path(path)
    if p.is_absolute():
        try:
            return str(p.relative_to(PROJECT_ROOT))
        except ValueError:
            return str(p)
    return str(p)


def run_cmd(cmd: list[str], timeout: int | None = None) -> tuple[int, str]:
    try:
        result = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        )
        return result.returncode, result.stdout
    except subprocess.TimeoutExpired as exc:
        return 124, (exc.stdout or "") + f"\n[ERROR] Command timed out after {timeout}s"
    except FileNotFoundError as exc:
        return 127, f"Command not found: {exc}"
    except Exception as exc:
        return 1, f"Unexpected error: {exc}"


def command_available(name: str) -> bool:
    return shutil.which(name) is not None


def load_text(path: str | Path, max_chars: int = 8000) -> str:
    p = abs_path(path)
    if not p.exists():
        return ""
    text = p.read_text(encoding="utf-8", errors="ignore")
    if len(text) > max_chars:
        return text[-max_chars:]
    return text


def load_json(path: str | Path) -> Any | None:
    p = abs_path(path)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return None


def file_size_mb(path: str | Path) -> float:
    p = abs_path(path)
    if not p.exists() or not p.is_file():
        return 0.0
    return p.stat().st_size / 1024 / 1024


def model_key(model_path: str) -> str:
    p = Path(model_path).with_suffix("")
    key = "_".join([part for part in p.parts if part not in ("/", "\\")])
    return (
        key.replace(".", "_")
        .replace("-", "_")
        .replace("/", "_")
        .replace("\\", "_")
        .replace(":", "")
    ) or "model"


def infer_type_from_path(model_path: str) -> str:
    lower = model_path.lower()
    if "mnist" in lower:
        return "mnist"
    if "mobilenet" in lower:
        return "mobilenetv2"
    if "resnet" in lower:
        return "resnet18"
    if "yolo" in lower:
        return "yolov5n"
    return "auto"


def get_paths() -> dict[str, Any]:
    model_path = st.session_state.get("model_path", "")
    key = model_key(model_path) if model_path else "model"
    return {
        "key": key,
        "int8_path": f"outputs/{key}_int8.onnx",
        "fp32_json": OUTPUTS_DIR / f"benchmark_{key}_fp32.json",
        "int8_json": OUTPUTS_DIR / f"benchmark_{key}_int8.json",
        "fp32_md": REPORTS_DIR / f"{key}_fp32_report.md",
        "fp32_html": REPORTS_DIR / f"{key}_fp32_report.html",
        "int8_md": REPORTS_DIR / f"{key}_int8_report.md",
        "int8_html": REPORTS_DIR / f"{key}_int8_report.html",
        "compare_md": REPORTS_DIR / f"{key}_compare_report.md",
        "compare_html": REPORTS_DIR / f"{key}_compare_report.html",
        "demo_dir": f"outputs/infer_demo_{key}",
        "package_dir": f"outputs/packages/{key}",
    }


def save_result(name: str, code: int, output: str) -> None:
    st.session_state[f"{name}_code"] = code
    st.session_state[f"{name}_output"] = output


def show_result(title: str, code: int, output: str, expanded: bool | None = None) -> None:
    if code == 0:
        st.success(f"✓ {title} 执行成功")
    else:
        st.error(f"✗ {title} 执行失败，退出码：{code}")
    if expanded is None:
        expanded = code != 0
    with st.expander("📋 查看命令输出", expanded=expanded):
        st.code(output or "(no output)", language="bash")


def show_saved_result(name: str, title: str, expanded: bool = False) -> None:
    code = st.session_state.get(f"{name}_code")
    output = st.session_state.get(f"{name}_output", "")
    if code is None:
        return
    show_result(title, code, output, expanded=expanded)


def reset_downstream_state() -> None:
    for key in [
        "model_checked", "int8_generated", "fp32_benchmarked", "int8_benchmarked",
        "fp32_report_generated", "fp32_html_generated", "int8_report_generated",
        "int8_html_generated", "compare_report_generated", "compare_html_generated",
        "cpp_demo_generated", "package_generated", "board_synced", "board_ran", "board_deployed",
    ]:
        st.session_state[key] = False
    for name in [
        "check", "quantize", "fp32_benchmark", "int8_benchmark", "fp32_report", "fp32_html",
        "int8_report", "int8_html", "compare_report", "compare_html", "cpp_demo", "deploy_qemu",
        "package", "board_sync", "board_run", "board_deploy", "matrix", "matrix_report", "pc_aipro_report",
    ]:
        st.session_state[f"{name}_code"] = None
        st.session_state[f"{name}_output"] = ""


def run_and_save(name: str, title: str, cmd: list[str], timeout: int | None = None, expanded: bool | None = None) -> tuple[int, str]:
    code, output = run_cmd(cmd, timeout=timeout)
    save_result(name, code, output)
    show_result(title, code, output, expanded=expanded)
    return code, output


def html_escape(value: Any) -> str:
    return escape(str(value), quote=True)


def command_text(cmd: list[str]) -> str:
    return " ".join(str(part) for part in cmd)


def render_command_preview(cmd: list[str], title: str = "将执行的命令") -> None:
    st.caption(title)
    st.markdown(f'<div class="cmd-preview">{html_escape(command_text(cmd))}</div>', unsafe_allow_html=True)


def status_class(status: Any) -> str:
    value = str(status or "NOT_RUN").upper()
    if value in {"PASS", "SUCCESS", "OK", "DONE"}:
        return "status-pass"
    if value in {"FAIL", "FAILED", "ERROR"}:
        return "status-fail"
    if value in {"RUNNING", "STARTED"}:
        return "status-running"
    if value in {"SKIP", "SKIPPED"}:
        return "status-skip"
    return ""


def status_chip(status: Any) -> str:
    label = str(status or "NOT_RUN")
    return f'<span class="status-chip {status_class(label)}">{html_escape(label)}</span>'


def render_kpi(label: str, value: Any, note: str = "", tone: str = "") -> None:
    st.markdown(
        f"""
        <div class="edge-kpi {html_escape(tone)}">
          <div class="edge-kpi-label">{html_escape(label)}</div>
          <div class="edge-kpi-value">{html_escape(value)}</div>
          <div class="edge-kpi-note">{html_escape(note)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_panel(title: str, note: str = "") -> None:
    st.markdown(
        f"""
        <div class="edge-panel">
          <div class="edge-panel-title">{html_escape(title)}</div>
          <div class="edge-panel-note">{html_escape(note)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def read_matrix() -> list[dict[str, Any]]:
    matrix = load_json(MATRIX_JSON)
    return matrix if isinstance(matrix, list) else []


def pass_count(items: list[dict[str, Any]], key: str) -> int:
    return sum(1 for item in items if str(item.get(key, "")).upper() == "PASS")


def latest_packages(limit: int = 12) -> list[Path]:
    if not PACKAGES_DIR.exists():
        return []
    dirs = [p for p in PACKAGES_DIR.iterdir() if p.is_dir()]
    return sorted(dirs, key=lambda p: p.stat().st_mtime, reverse=True)[:limit]


def model_options() -> list[str]:
    candidates = [
        "models/zoo/mnist/model.onnx",
        "models/zoo/mobilenetv2/model.onnx",
        "models/zoo/mobilenetv2/model_opset11.onnx",
        "models/zoo/resnet18/model.onnx",
        "models/zoo/yolov5n/model.onnx",
        "models/zoo/yolov5n_opset11/model.onnx",
        "examples/mnist/model.onnx",
    ]
    found: list[str] = []
    for pattern in ["models/**/*.onnx", "examples/**/*.onnx", "outputs/**/*.onnx"]:
        for path in PROJECT_ROOT.glob(pattern):
            if path.is_file():
                found.append(rel(path))
    merged = candidates + found
    return sorted(dict.fromkeys([p for p in merged if abs_path(p).exists()]))


def save_uploaded_file(uploaded_file: Any, folder: str) -> str:
    upload_dir = PROJECT_ROOT / "inputs" / folder
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(uploaded_file.name).name.replace(" ", "_")
    target = upload_dir / safe_name
    target.write_bytes(uploaded_file.getbuffer())
    return rel(target)


def maybe_image(path: str | Path) -> bool:
    return Path(path).suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp", ".webp"}


def render_file_download(path: str | Path, label: str | None = None) -> None:
    p = abs_path(path)
    if not p.exists() or not p.is_file():
        return
    st.download_button(
        label or f"下载 {p.name}",
        data=p.read_bytes(),
        file_name=p.name,
        mime="application/octet-stream",
        use_container_width=True,
        key=f"download_{model_key(str(p))}_{int(p.stat().st_mtime)}",
    )


def render_json_file(path: str | Path, title: str) -> None:
    data = load_json(path)
    if data is None:
        return
    with st.expander(title, expanded=False):
        st.json(data)
        render_file_download(path)


def render_file_table(folder: str | Path) -> None:
    base = abs_path(folder)
    if not base.exists():
        st.info("目录暂不存在。")
        return
    rows = []
    for p in sorted(base.iterdir(), key=lambda item: (item.is_file(), item.name.lower())):
        rows.append({
            "名称": p.name,
            "类型": "目录" if p.is_dir() else "文件",
            "大小 MB": "-" if p.is_dir() else f"{p.stat().st_size / 1024 / 1024:.4f}",
            "更新时间": datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        })
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.caption("目录为空。")


def render_package_preview(package_dir: str | Path) -> None:
    pkg = abs_path(package_dir)
    if not pkg.exists():
        st.info("部署包还没有生成。")
        return
    st.success(f"部署包已存在：`{rel(pkg)}`")
    render_file_table(pkg)
    for filename in ["package_result.json", "model.json", "board_result.json", "convert_result.json"]:
        render_json_file(pkg / filename, filename)
    image_candidates = [
        p for p in pkg.glob("*")
        if p.is_file() and maybe_image(p) and ("result" in p.name.lower() or "info" in p.name.lower())
    ]
    if image_candidates:
        st.markdown("#### 推理图片结果")
        for image in image_candidates[:4]:
            st.image(str(image), caption=rel(image), use_container_width=True)


def render_pipeline_steps() -> None:
    steps = [
        ("模型确认", st.session_state.get("model_confirmed"), "选择 ONNX 并读取结构"),
        ("ONNX 检查", st.session_state.get("model_checked"), "确认模型可加载"),
        ("Benchmark", st.session_state.get("fp32_benchmarked"), "开发端性能采样"),
        ("部署打包", st.session_state.get("package_generated"), "生成 model.json/input.npy"),
        ("板端运行", st.session_state.get("board_ran") or st.session_state.get("board_deployed"), "ATC/airloader 推理"),
        ("报告矩阵", MATRIX_JSON.exists(), "汇总 JSON 生成报告"),
    ]
    import textwrap
    html = ['<div class="step-rail">']
    for title, done, note in steps:
        html.append(textwrap.dedent(f"""\
        <div class="step-box {'done' if done else 'wait'}">
          <div class="step-title">{html_escape(title)}</div>
          <div class="step-note">{html_escape(note)}</div>
          <div style="margin-top:8px;">{status_chip('PASS' if done else 'NOT_RUN')}</div>
        </div>"""))
    html.append("</div>")
    st.markdown("".join(html), unsafe_allow_html=True)


def render_matrix_status_table(matrix: list[dict[str, Any]]) -> None:
    if not matrix:
        st.info("还没有矩阵数据。可以先到「报告中心」生成 Matrix。")
        return
    rows = []
    for item in matrix:
        rows.append({
            "模型": item.get("model", "-"),
            "类型": item.get("model_type", "-"),
            "Package": item.get("package", "NOT_RUN"),
            "Board Sync": item.get("board_sync", "NOT_RUN"),
            "OM Convert": item.get("om_convert", "NOT_RUN"),
            "Board Run": item.get("board_run", "NOT_RUN"),
            "板端延迟 ms": item.get("board_latency_ms"),
            "预测": item.get("predict"),
            "标签": item.get("predict_label") or item.get("top1_label"),
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════
#  Environment install helpers
# ═══════════════════════════════════════════

def install_basic_env() -> tuple[int, str]:
    return run_cmd(["sudo", "-n", "dnf", "install", "-y", "cmake", "make", "gcc", "gcc-c++"], timeout=120)


def install_onnxruntime_sdk() -> tuple[int, str]:
    cmd = [
        "bash", "-lc",
        """
set -e
mkdir -p third_party
cd third_party
if [ ! -d onnxruntime-linux-x64-1.26.0 ]; then
  wget -c https://github.com/microsoft/onnxruntime/releases/download/v1.26.0/onnxruntime-linux-x64-1.26.0.tgz
  tar -xzf onnxruntime-linux-x64-1.26.0.tgz
fi
if [ ! -d onnxruntime-linux-aarch64-1.26.0 ]; then
  wget -c https://github.com/microsoft/onnxruntime/releases/download/v1.26.0/onnxruntime-linux-aarch64-1.26.0.tgz
  tar -xzf onnxruntime-linux-aarch64-1.26.0.tgz
fi
""",
    ]
    return run_cmd(cmd, timeout=300)


def install_aarch64_sdk() -> tuple[int, str]:
    cmd = [
        "bash", "-lc",
        """
set -e
mkdir -p /tmp/edgeai-tools
cd /tmp/edgeai-tools
wget -c https://repo.openeuler.org/openEuler-24.03-LTS/embedded_img/aarch64/qemu-aarch64/openeuler-glibc-x86_64-openeuler-image-aarch64-qemu-aarch64-toolchain-24.03-LTS.sh
chmod +x openeuler-glibc-x86_64-openeuler-image-aarch64-qemu-aarch64-toolchain-24.03-LTS.sh
sudo -n ./openeuler-glibc-x86_64-openeuler-image-aarch64-qemu-aarch64-toolchain-24.03-LTS.sh -y -d /opt/openeuler-aarch64
""",
    ]
    return run_cmd(cmd, timeout=600)


# ═══════════════════════════════════════════
#  Sidebar
# ═══════════════════════════════════════════

def render_env_help() -> None:
    with st.sidebar.expander("⚙️ 配置缺失环境", expanded=False):
        if st.button("🔧 安装 cmake / make / gcc / g++", use_container_width=True):
            code, output = install_basic_env()
            save_result("install_basic_env", code, output)
            if code == 0:
                st.success("基础编译环境安装完成")
            else:
                st.error("基础编译环境安装失败")

        if st.button("📦 下载 ONNX Runtime x64/aarch64 SDK", use_container_width=True):
            code, output = install_onnxruntime_sdk()
            save_result("install_ort_sdk", code, output)
            if code == 0:
                st.success("ONNX Runtime SDK 配置完成")
            else:
                st.error("ONNX Runtime SDK 配置失败")

        if st.button("🖥️ 安装 openEuler aarch64 SDK", use_container_width=True):
            code, output = install_aarch64_sdk()
            save_result("install_aarch64_sdk", code, output)
            if code == 0:
                st.success("aarch64 SDK 安装完成")
            else:
                st.error("aarch64 SDK 安装失败")

        st.info("QEMU、ATC、CANN 依赖较重，暂不建议 WebUI 自动安装。")


def render_sidebar() -> None:
    st.sidebar.markdown("""
    <div style="text-align:center;padding:10px 0 6px 0;">
      <div style="font-size:1.3rem;font-weight:700;background:linear-gradient(135deg,#06b6d4,#3b82f6);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">
        ⚡ EdgeAI Console
      </div>
      <div style="font-size:0.7rem;color:#64748b;letter-spacing:0.1em;">DEPLOY KIT v0.1.0</div>
    </div>
    """, unsafe_allow_html=True)

    st.sidebar.divider()

    st.sidebar.markdown("##### 📍 项目路径")
    st.sidebar.code(str(PROJECT_ROOT), language=None)
    st.sidebar.caption(f"outputs → `{rel(OUTPUTS_DIR)}`")
    st.sidebar.caption(f"reports → `{rel(REPORTS_DIR)}`")

    st.sidebar.divider()
    st.sidebar.markdown("##### 🔍 环境检测")

    if st.sidebar.button("🔄 重新检测环境", use_container_width=True):
        st.rerun()

    checks = [
        ("🧠 edgeai CLI", "edgeai"),
        ("📐 cmake", "cmake"),
        ("🔨 make", "make"),
        ("⚙️ gcc", "gcc"),
        ("⚙️ g++", "g++"),
        ("🖥️ qemu", "qemu-system-aarch64"),
        ("📡 atc", "atc"),
    ]
    missing_basic = []
    for label, cmd in checks:
        if command_available(cmd):
            st.sidebar.success(f"{label}")
        else:
            st.sidebar.warning(f"{label} — missing")
            if cmd in ["cmake", "make", "gcc", "g++"]:
                missing_basic.append(cmd)

    sdk_env = Path("/opt/openeuler-aarch64/environment-setup-aarch64-openeuler-linux")
    if sdk_env.exists():
        st.sidebar.success("📦 aarch64 SDK")
    else:
        st.sidebar.warning("📦 aarch64 SDK — missing")

    if missing_basic:
        if st.sidebar.button("⚡ 一键安装基础编译环境", use_container_width=True):
            code, output = install_basic_env()
            save_result("env_install", code, output)
            if code == 0:
                st.sidebar.success("基础编译环境安装完成")
            else:
                st.sidebar.error("自动安装失败")

    render_env_help()


# ═══════════════════════════════════════════
#  Overview
# ═══════════════════════════════════════════

def render_overview_tab() -> None:
    st.markdown("### 总览工作台")
    st.caption("把模型、部署包、板端结果和报告矩阵放在同一个视图里，先看全局状态，再进入具体步骤。")

    matrix = read_matrix()
    packages = latest_packages()
    board_pass = pass_count(matrix, "board_run")
    om_pass = pass_count(matrix, "om_convert")
    benchmark_pass = pass_count(matrix, "benchmark")
    current_model = st.session_state.get("model_path", "未选择")

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        render_kpi("当前模型", Path(current_model).name if current_model != "未选择" else current_model, st.session_state.get("model_type", "等待选择"), "blue")
    with k2:
        render_kpi("矩阵模型数", len(matrix), "outputs/model_matrix/matrix.json", "green")
    with k3:
        render_kpi("板端跑通", f"{board_pass}/{len(matrix)}" if matrix else "0", "Board Run PASS", "teal")
    with k4:
        render_kpi("部署包", len(packages), "outputs/packages", "amber")

    st.markdown("#### 当前流程")
    render_pipeline_steps()

    st.divider()
    col_a, col_b = st.columns([1.2, 1])
    with col_a:
        st.markdown("#### 模型矩阵快照")
        render_matrix_status_table(matrix)
    with col_b:
        st.markdown("#### 快速操作")
        if st.button("生成 / 刷新 Matrix", use_container_width=True, type="primary"):
            with st.spinner("正在生成矩阵..."):
                run_and_save("matrix", "Matrix", ["edgeai", "matrix"], timeout=120)
        if st.button("生成矩阵报告", use_container_width=True):
            with st.spinner("正在生成报告..."):
                run_and_save("matrix_report", "Matrix Report", ["edgeai", "matrix-report"], timeout=120)
        if st.button("生成 PC/AIPro 对比", use_container_width=True):
            with st.spinner("正在生成对比报告..."):
                run_and_save("pc_aipro_report", "PC/AIPro Report", ["edgeai", "pc-aipro-report"], timeout=120)
        show_saved_result("matrix", "Matrix")
        show_saved_result("matrix_report", "Matrix Report")
        show_saved_result("pc_aipro_report", "PC/AIPro Report")

    st.divider()
    st.markdown("#### 最近部署包")
    if packages:
        package_choice = st.selectbox("查看部署包", [rel(p) for p in packages])
        render_package_preview(package_choice)
    else:
        st.info("暂无部署包。")


# ═══════════════════════════════════════════
#  Page 1: model select
# ═══════════════════════════════════════════

def render_model_tab() -> None:
    st.markdown("### 🧠 模型选择")
    st.caption("选择、上传或输入 ONNX 模型路径；确认后会自动读取模型信息，并作为后续 Check、Benchmark、QEMU、板端部署的默认模型。")

    upload_col, image_col, json_col = st.columns(3)
    with upload_col:
        uploaded_model = st.file_uploader("上传 ONNX 模型", type=["onnx"], key="onnx_upload")
        if uploaded_model is not None:
            saved = save_uploaded_file(uploaded_model, "models")
            st.session_state["uploaded_model_path"] = saved
            st.success(f"已保存：`{saved}`")
    with image_col:
        uploaded_input = st.file_uploader("上传测试图片 / 输入文件", type=["png", "jpg", "jpeg", "bmp", "webp", "npy", "bin", "txt", "csv"], key="input_upload")
        if uploaded_input is not None:
            saved = save_uploaded_file(uploaded_input, "inputs")
            st.session_state["uploaded_input_path"] = saved
            st.success(f"已保存：`{saved}`")
            if maybe_image(saved):
                st.image(str(abs_path(saved)), caption=saved, use_container_width=True)
    with json_col:
        uploaded_json = st.file_uploader("上传 B 端 JSON", type=["json"], key="json_upload")
        if uploaded_json is not None:
            saved = save_uploaded_file(uploaded_json, "json")
            st.session_state["uploaded_json_path"] = saved
            st.success(f"已保存：`{saved}`")

    st.divider()

    existing_models = model_options()
    mode_options = ["预置 / 扫描模型", "上传模型", "自定义路径"]
    if hasattr(st, "segmented_control"):
        mode = st.segmented_control("选择方式", mode_options, default="预置 / 扫描模型")
    else:
        mode = st.radio("选择方式", mode_options, horizontal=True)

    if mode == "预置 / 扫描模型":
        if not existing_models:
            st.warning("未检测到预置模型，请使用自定义路径。")
            candidate = ""
        else:
            candidate = st.selectbox("选择模型", existing_models)
    elif mode == "上传模型":
        candidate = st.session_state.get("uploaded_model_path", "")
        st.text_input("上传模型路径", value=candidate, disabled=True)
    else:
        candidate = st.text_input("模型路径", value=st.session_state.get("model_path", ""), placeholder="例如：models/zoo/mobilenetv2/model.onnx")

    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("🚀 确认模型", type="primary", use_container_width=True):
            if not candidate:
                st.error("请先选择或输入模型路径。")
                return
            if not abs_path(candidate).exists():
                st.session_state["model_path"] = candidate
                st.session_state["model_confirmed"] = False
                st.error("模型文件不存在。")
                st.code(candidate)
                return
            st.session_state["model_path"] = candidate
            st.session_state["model_confirmed"] = True
            st.session_state["model_type"] = infer_type_from_path(candidate)
            reset_downstream_state()
            code, output = run_cmd(["edgeai", "model-info", "--model", candidate])
            st.session_state["model_info_code"] = code
            st.session_state["model_info_output"] = output
            if code == 0:
                st.success("✓ 模型确认成功")
            else:
                st.warning("模型存在，但 model-info 执行失败。")
    with col2:
        if candidate:
            inferred = infer_type_from_path(candidate)
            st.markdown(
                f"""
                <div class="edge-panel">
                  <div class="edge-panel-title">待确认模型</div>
                  <div class="edge-panel-note">路径：{html_escape(candidate)} · 类型推断：{html_escape(inferred)} · 大小：{file_size_mb(candidate):.2f} MB</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    if st.session_state.get("model_confirmed"):
        model_path = st.session_state["model_path"]
        st.divider()
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.markdown(f"""
            <div class="tech-metric">
              <div class="tech-metric-label">当前模型</div>
              <div class="tech-metric-value" style="font-size:0.95rem;">{Path(model_path).name}</div>
            </div>
            """, unsafe_allow_html=True)
        with col_b:
            st.markdown(f"""
            <div class="tech-metric">
              <div class="tech-metric-label">模型大小</div>
              <div class="tech-metric-value">{file_size_mb(model_path):.2f} MB</div>
            </div>
            """, unsafe_allow_html=True)
        with col_c:
            model_type = st.session_state.get("model_type", "auto")
            st.markdown(f"""
            <div class="tech-metric">
              <div class="tech-metric-label">检测类型</div>
              <div class="tech-metric-value" style="font-size:0.95rem;">{model_type.upper()}</div>
            </div>
            """, unsafe_allow_html=True)
        output = st.session_state.get("model_info_output", "")
        if output:
            with st.expander("📋 model-info 详情"):
                st.code(output, language="text")
        paths = get_paths()
        st.markdown("#### 后续默认产物路径")
        artifact_rows = [
            {"用途": "INT8 模型", "路径": paths["int8_path"]},
            {"用途": "FP32 Benchmark JSON", "路径": rel(paths["fp32_json"])},
            {"用途": "部署包", "路径": paths["package_dir"]},
            {"用途": "C++ Demo", "路径": paths["demo_dir"]},
        ]
        st.dataframe(pd.DataFrame(artifact_rows), use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════
#  Page 2: check / quantize
# ═══════════════════════════════════════════

def render_check_quantize_tab() -> None:
    st.markdown("### 🔍 模型检查 & 量化")
    if not st.session_state.get("model_confirmed"):
        st.info("ℹ️ 请先在「模型选择」页面确认模型。")
        return

    model_path = st.session_state["model_path"]
    paths = get_paths()

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("""
        <div class="tech-card">
          <h3>📋 ONNX 合法性检查</h3>
        """, unsafe_allow_html=True)
        st.code(model_path)
        st.metric("原始模型大小", f"{file_size_mb(model_path):.4f} MB")
        render_command_preview(["edgeai", "check", "--model", model_path])
        if st.button("✅ 执行 Check ONNX", type="primary"):
            with st.spinner("正在检查模型..."):
                code, output = run_cmd(["edgeai", "check", "--model", model_path])
                save_result("check", code, output)
                st.session_state["model_checked"] = code == 0
        show_saved_result("check", "ONNX Check")
        if st.session_state.get("model_checked"):
            st.success("✓ ONNX Check 已通过")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_b:
        st.markdown("""
        <div class="tech-card">
          <h3>⚡ INT8 动态量化</h3>
        """, unsafe_allow_html=True)
        if not st.session_state.get("model_checked"):
            st.info("Check 通过后可执行量化。")
        else:
            int8_path = paths["int8_path"]
            st.caption("量化输出路径")
            st.code(int8_path)
            render_command_preview(["edgeai", "quantize", "--model", model_path, "--output", int8_path])
            if st.button("🔮 执行 Quantize INT8"):
                with st.spinner("正在量化模型..."):
                    code, output = run_cmd([
                        "edgeai", "quantize", "--model", model_path, "--output", int8_path,
                    ])
                    if code == 0 and (PROJECT_ROOT / int8_path).exists():
                        compat_path = PROJECT_ROOT / "outputs" / "model_int8.onnx"
                        shutil.copy2(PROJECT_ROOT / int8_path, compat_path)
                        output += "\n[WebUI] Compatibility copy saved to: outputs/model_int8.onnx\n"
                    save_result("quantize", code, output)
                    st.session_state["int8_generated"] = code == 0 and (PROJECT_ROOT / int8_path).exists()
            show_saved_result("quantize", "INT8 Quantize")
            if st.session_state.get("int8_generated"):
                st.success("✓ 本次会话已生成 INT8 模型")
                c1, c2 = st.columns(2)
                c1.metric("INT8 模型大小", f"{file_size_mb(int8_path):.4f} MB")
                if file_size_mb(int8_path) > 0:
                    c2.metric("压缩率", f"{file_size_mb(model_path) / file_size_mb(int8_path):.2f}x")
                    render_file_download(int8_path, "下载 INT8 ONNX")
        st.markdown("</div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════
#  Page 3: benchmark/report
# ═══════════════════════════════════════════

def render_single_benchmark_table(title: str, data: dict[str, Any]) -> None:
    row = {
        "Model": title,
        "Size MB": data.get("model_size_mb", 0),
        "Avg ms": data.get("avg_latency_ms", 0),
        "P50 ms": data.get("p50_latency_ms", data.get("p50_ms", 0)),
        "P95 ms": data.get("p95_latency_ms", data.get("p95_ms", 0)),
        "P99 ms": data.get("p99_latency_ms", data.get("p99_ms", 0)),
    }
    st.dataframe(pd.DataFrame([row]), use_container_width=True)


def render_compare_table(fp32: dict[str, Any], int8: dict[str, Any]) -> None:
    rows = []
    for name, data in [("FP32", fp32), ("INT8", int8)]:
        rows.append({
            "Model": name,
            "Size MB": data.get("model_size_mb", 0),
            "Avg ms": data.get("avg_latency_ms", 0),
            "P50 ms": data.get("p50_latency_ms", data.get("p50_ms", 0)),
            "P95 ms": data.get("p95_latency_ms", data.get("p95_ms", 0)),
            "P99 ms": data.get("p99_latency_ms", data.get("p99_ms", 0)),
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True)
    fp32_avg = fp32.get("avg_latency_ms", 0) or 0
    int8_avg = int8.get("avg_latency_ms", 0) or 0
    fp32_size = fp32.get("model_size_mb", 0) or 0
    int8_size = int8.get("model_size_mb", 0) or 0
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"""
        <div class="tech-metric">
          <div class="tech-metric-label">⚡ Speedup</div>
          <div class="tech-metric-value">{fp32_avg / int8_avg if int8_avg else 0:.2f}x</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="tech-metric">
          <div class="tech-metric-label">📦 压缩率</div>
          <div class="tech-metric-value">{fp32_size / int8_size if int8_size else 0:.2f}x</div>
        </div>
        """, unsafe_allow_html=True)


def render_benchmark_tab() -> None:
    st.markdown("### ⚡ Benchmark & 报告")
    if not st.session_state.get("model_confirmed"):
        st.info("ℹ️ 请先在「模型选择」页面确认模型。")
        return

    model_path = st.session_state["model_path"]
    paths = get_paths()
    col_repeat, col_input, col_type = st.columns([1, 2, 1])
    with col_repeat:
        repeat = st.number_input("Benchmark repeat 次数", min_value=1, max_value=500, value=50, step=10)
    with col_input:
        benchmark_input = st.text_input(
            "真实输入文件（可选）",
            value=st.session_state.get("uploaded_input_path", ""),
            placeholder="例如：photo/cat.png；留空使用随机 dummy",
        )
    with col_type:
        inferred = infer_type_from_path(model_path)
        type_options = ["auto", "mnist", "mobilenetv2", "resnet18", "yolov5n"]
        default_idx = type_options.index(inferred) if inferred in type_options else 0
        bench_type = st.selectbox("模型类型", type_options, index=default_idx, key="bench_type")

    fp32_cmd = ["edgeai", "benchmark", "--model", model_path, "--repeat", str(repeat), "--output", rel(paths["fp32_json"])]
    if benchmark_input.strip():
        fp32_cmd += ["--input", benchmark_input.strip()]
    if bench_type != "auto":
        fp32_cmd += ["--type", bench_type]
    render_command_preview(fp32_cmd)

    st.markdown("#### 🔵 FP32 Benchmark 与报告")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("▶️ 执行 FP32 Benchmark", type="primary"):
            with st.spinner("正在运行 Benchmark..."):
                code, output = run_cmd(fp32_cmd)
                save_result("fp32_benchmark", code, output)
                st.session_state["fp32_benchmarked"] = code == 0 and paths["fp32_json"].exists()
    with col2:
        if st.button("📝 生成 FP32 Markdown"):
            if not st.session_state.get("fp32_benchmarked"):
                st.warning("请先执行 FP32 Benchmark。")
            else:
                code, output = run_cmd(["edgeai", "report", "--input", rel(paths["fp32_json"]), "--output", rel(paths["fp32_md"])])
                save_result("fp32_report", code, output)
                st.session_state["fp32_report_generated"] = code == 0
    with col3:
        if st.button("🌐 生成 FP32 HTML"):
            if not st.session_state.get("fp32_report_generated"):
                st.warning("请先生成 Markdown 报告。")
            else:
                code, output = run_cmd(["edgeai", "html", "--input", rel(paths["fp32_md"]), "--output", rel(paths["fp32_html"])])
                save_result("fp32_html", code, output)
                st.session_state["fp32_html_generated"] = code == 0
    show_saved_result("fp32_benchmark", "FP32 Benchmark")
    show_saved_result("fp32_report", "FP32 Markdown Report")
    show_saved_result("fp32_html", "FP32 HTML Report")

    if st.session_state.get("fp32_benchmarked"):
        fp32 = load_json(paths["fp32_json"])
        if fp32:
            render_single_benchmark_table("FP32", fp32)
            annotated = fp32.get("annotated_image")
            if annotated and abs_path(annotated).exists():
                st.image(str(abs_path(annotated)), caption=f"识别结果：{annotated}", use_container_width=True)
            render_json_file(paths["fp32_json"], "FP32 benchmark JSON")
    if st.session_state.get("fp32_report_generated") and paths["fp32_md"].exists():
        with st.expander("📄 查看 FP32 Markdown 报告"):
            st.markdown(load_text(paths["fp32_md"], max_chars=50000))

    st.divider()
    st.markdown("#### 🟣 INT8 Benchmark 与对比报告")
    if not st.session_state.get("int8_generated"):
        st.info("未生成 INT8 模型，跳过。")
        return

    int8_path = paths["int8_path"]
    int8_cmd = ["edgeai", "benchmark", "--model", int8_path, "--repeat", str(repeat), "--output", rel(paths["int8_json"])]
    if benchmark_input.strip():
        int8_cmd += ["--input", benchmark_input.strip()]
    if bench_type != "auto":
        int8_cmd += ["--type", bench_type]
    render_command_preview(int8_cmd, "INT8 Benchmark 命令")
    col4, col5, col6 = st.columns(3)
    with col4:
        if st.button("▶️ 执行 INT8 Benchmark"):
            with st.spinner("正在运行 INT8 Benchmark..."):
                code, output = run_cmd(int8_cmd)
                save_result("int8_benchmark", code, output)
                st.session_state["int8_benchmarked"] = code == 0
    with col5:
        if st.button("📝 生成 INT8 报告"):
            if not st.session_state.get("int8_benchmarked"):
                st.warning("请先执行 INT8 Benchmark。")
            else:
                code, output = run_cmd(["edgeai", "report", "--input", rel(paths["int8_json"]), "--output", rel(paths["int8_md"])])
                save_result("int8_report", code, output)
                st.session_state["int8_report_generated"] = code == 0
                if code == 0:
                    code2, output2 = run_cmd(["edgeai", "html", "--input", rel(paths["int8_md"]), "--output", rel(paths["int8_html"])])
                    save_result("int8_html", code2, output2)
                    st.session_state["int8_html_generated"] = code2 == 0
    with col6:
        if st.button("📊 生成 FP32 vs INT8 对比"):
            if not st.session_state.get("fp32_benchmarked") or not st.session_state.get("int8_benchmarked"):
                st.warning("请先执行 FP32 和 INT8 Benchmark。")
            else:
                code, output = run_cmd(["edgeai", "compare", "--fp32", rel(paths["fp32_json"]), "--int8", rel(paths["int8_json"]), "--output", rel(paths["compare_md"])])
                save_result("compare_report", code, output)
                st.session_state["compare_report_generated"] = code == 0
                if code == 0:
                    code2, output2 = run_cmd(["edgeai", "html", "--input", rel(paths["compare_md"]), "--output", rel(paths["compare_html"])])
                    save_result("compare_html", code2, output2)

    show_saved_result("int8_benchmark", "INT8 Benchmark")
    show_saved_result("compare_report", "Compare Report")

    if st.session_state.get("fp32_benchmarked") and st.session_state.get("int8_benchmarked"):
        fp32 = load_json(paths["fp32_json"])
        int8 = load_json(paths["int8_json"])
        if fp32 and int8:
            render_compare_table(fp32, int8)
    if st.session_state.get("int8_benchmarked"):
        render_json_file(paths["int8_json"], "INT8 benchmark JSON")
    if st.session_state.get("compare_report_generated") and paths["compare_md"].exists():
        with st.expander("📄 查看 FP32 vs INT8 对比报告", expanded=True):
            st.markdown(load_text(paths["compare_md"], max_chars=50000))


# ═══════════════════════════════════════════
#  Page 4: ONNX Runtime / QEMU route
# ═══════════════════════════════════════════

def render_ort_qemu_tab() -> None:
    st.markdown("### 🖥️ ONNX Runtime / C++ / QEMU")
    st.caption("生成 C++ ONNX Runtime 推理工程，支持 x86_64 / ARM64 编译与 QEMU 部署验证。")

    paths = get_paths()
    model_options = []
    if st.session_state.get("model_confirmed"):
        model_options.append("原始 FP32 ONNX")
    if st.session_state.get("int8_generated") and abs_path(paths["int8_path"]).exists():
        model_options.append("量化 INT8 ONNX")
    model_options.append("自定义模型路径")
    selected_model_type = st.radio("模型来源", model_options, horizontal=True)
    if selected_model_type == "原始 FP32 ONNX":
        model_for_demo = st.session_state["model_path"]
    elif selected_model_type == "量化 INT8 ONNX":
        model_for_demo = paths["int8_path"]
    else:
        model_for_demo = st.text_input("自定义模型路径", value="", placeholder="例如：models/zoo/mobilenetv2/model.onnx")

    demo_key = model_key(model_for_demo) if model_for_demo else "custom_model"
    demo_dir = st.text_input("C++ Demo 输出目录", value=f"outputs/infer_demo_{demo_key}")

    if st.button("🚀 Generate C++ Demo", type="primary"):
        if not model_for_demo or not abs_path(model_for_demo).exists():
            st.error("模型文件不存在。")
        else:
            with st.spinner("正在生成 C++ Demo..."):
                code, output = run_cmd(["edgeai", "generate", "--model", model_for_demo, "--output", demo_dir])
                save_result("cpp_demo", code, output)
                st.session_state["cpp_demo_generated"] = code == 0
                st.session_state["cpp_demo_model"] = model_for_demo
                st.session_state["cpp_demo_dir"] = demo_dir
    show_saved_result("cpp_demo", "Generate C++ Demo")
    if st.session_state.get("cpp_demo_generated"):
        st.success("✓ C++ Demo 已生成")
        actual_demo_dir = abs_path(st.session_state.get("cpp_demo_dir", demo_dir))
        if actual_demo_dir.exists():
            st.write([rel(p) for p in actual_demo_dir.glob("*")])

    st.divider()
    st.markdown("#### 🔨 编译脚本")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔵 运行 x86_64 Build"):
            script = PROJECT_ROOT / "scripts" / "build_x86_64_demo.sh"
            if not script.exists():
                st.warning("scripts/build_x86_64_demo.sh 不存在。")
            else:
                with st.spinner("编译中..."):
                    code, output = run_cmd(["bash", rel(script)])
                    save_result("x86_build", code, output)
    with col2:
        if st.button("🟠 运行 ARM64 Build"):
            script = PROJECT_ROOT / "scripts" / "build_arm64_demo.sh"
            if not script.exists():
                st.warning("scripts/build_arm64_demo.sh 不存在。")
            else:
                with st.spinner("交叉编译中..."):
                    code, output = run_cmd(["bash", rel(script)])
                    save_result("arm64_build", code, output)
    show_saved_result("x86_build", "x86_64 Build")
    show_saved_result("arm64_build", "ARM64 Build")

    st.divider()
    st.markdown("#### 🖥️ QEMU 部署验证")
    st.caption("该功能依赖 QEMU、kernel、rootfs/initramfs、ARM64 ONNX Runtime 等环境。")
    qemu_model = st.text_input("QEMU 使用模型", value=st.session_state.get("cpp_demo_model", st.session_state.get("model_path", "")))
    qemu_input = st.text_input("QEMU 输入文件（可选）", value=st.session_state.get("uploaded_input_path", ""), placeholder="例如：photo/1.png；留空使用随机输入")
    q1, q2 = st.columns(2)
    with q1:
        qemu_kernel = st.text_input("Kernel Image", value="/root/qemu-5.0.0/linux-5.10/arch/arm64/boot/Image", key="qemu_kernel")
        qemu_initramfs = st.text_input("Initramfs", value="/root/initramfs.cpio", key="qemu_initramfs")
    with q2:
        qemu_output = st.text_input("QEMU 输出目录", value="outputs/qemu_deploy", key="qemu_output")
        qemu_memory = st.text_input("QEMU 内存", value="1024M", key="qemu_memory")
    qemu_ort = st.text_input("ARM64 ONNX Runtime Root", value="third_party/onnxruntime-aarch64", key="qemu_ort")
    qemu_cmd = ["edgeai", "deploy-qemu", "--model", qemu_model, "--kernel", qemu_kernel, "--initramfs", qemu_initramfs, "--output", qemu_output, "--memory", qemu_memory, "--onnxruntime-root", qemu_ort]
    if qemu_input.strip():
        qemu_cmd += ["--input", qemu_input.strip()]
    render_command_preview(qemu_cmd)
    if st.button("📖 查看 deploy-qemu 帮助"):
        code, output = run_cmd(["edgeai", "deploy-qemu", "--help"])
        save_result("deploy_qemu_help", code, output)
    show_saved_result("deploy_qemu_help", "deploy-qemu --help")
    if st.button("▶️ 尝试执行 deploy-qemu"):
        if not qemu_model:
            st.error("请先填写模型路径。")
        else:
            with st.spinner("QEMU 部署中，可能需要较长时间..."):
                code, output = run_cmd(qemu_cmd, timeout=300)
                save_result("deploy_qemu", code, output)
    show_saved_result("deploy_qemu", "deploy-qemu")
    if abs_path(qemu_output).exists():
        with st.expander("QEMU 输出目录", expanded=False):
            render_file_table(qemu_output)
            render_json_file(abs_path(qemu_output) / "deploy_result.json", "deploy_result.json")


# ═══════════════════════════════════════════
#  Page 5: board deploy route
# ═══════════════════════════════════════════

def render_board_tab() -> None:
    st.markdown("### 🍊 香橙派 AIPro 部署")
    st.caption("通过 SSH 远程同步和运行香橙派板端模型。")

    col_a, col_b = st.columns([2, 1])
    with col_a:
        default_model = st.session_state.get("model_path", "models/zoo/mnist/model.onnx")
        board_model = st.text_input("ONNX 模型路径", value=default_model)
    with col_b:
        inferred = infer_type_from_path(board_model)
        type_options = ["auto", "mnist", "mobilenetv2", "resnet18", "yolov5n"]
        default_idx = type_options.index(inferred) if inferred in type_options else 0
        model_type = st.selectbox("模型类型", type_options, index=default_idx)

    input_path = st.text_input("输入文件（可选）", value=st.session_state.get("uploaded_input_path", ""), placeholder="image / .npy / .bin / .txt / .csv，留空使用内置 dummy")
    json_path = st.text_input("B-side JSON（可选）", value=st.session_state.get("uploaded_json_path", ""))
    package_output = st.text_input("部署包输出目录", value=f"outputs/packages/{model_key(board_model) if board_model else 'model'}")

    st.markdown("#### 🔗 板端连接参数")
    c1, c2, c3 = st.columns(3)
    with c1:
        host = st.text_input("香橙派 IP", value=st.session_state.get("board_host", ""), placeholder="192.168.1.100")
    with c2:
        user = st.text_input("用户名", value=st.session_state.get("board_user", "HwHiAiUser"))
    with c3:
        port = st.number_input("端口", min_value=1, max_value=65535, value=int(st.session_state.get("board_port", 7891)), step=1)
    remote_root = st.text_input("远程目录", value="~/edgeai_models")
    c4, c5 = st.columns(2)
    with c4:
        wait = st.number_input("等待秒数", min_value=0.0, max_value=60.0, value=3.0, step=1.0)
    with c5:
        min_free_gb = st.number_input("最小剩余空间 GB", min_value=0.0, max_value=100.0, value=2.0, step=0.5)
    force_convert = st.checkbox("强制重新 ATC 转换（默认关闭，优先复用板端已有 model.om）", value=False)
    st.caption("MobileNetV2 / YOLOv5n 在板端 ATC 转换可能耗时较长。已验证过的模型建议关闭强制转换，直接复用 OM。")
    st.session_state["board_host"] = host
    st.session_state["board_user"] = user
    st.session_state["board_port"] = int(port)

    def base_package_cmd() -> list[str]:
        cmd = ["edgeai", "package", "--model", board_model, "--output", package_output]
        if model_type != "auto":
            cmd += ["--type", model_type]
        if input_path.strip():
            cmd += ["--input", input_path.strip()]
        if json_path.strip():
            cmd += ["--json", json_path.strip()]
        return cmd

    sync_cmd = ["edgeai", "board-sync", "--host", host or "<board-ip>", "--user", user, "--package", package_output, "--remote-root", remote_root, "--min-free-gb", str(min_free_gb)]
    run_cmd_preview = ["edgeai", "board-run", "--host", host or "<board-ip>", "--user", user, "--port", str(int(port)), "--package", package_output, "--remote-root", remote_root, "--wait", str(wait), "--output", package_output]
    deploy_cmd = ["edgeai", "board-deploy", "--model", board_model, "--host", host or "<board-ip>", "--user", user, "--port", str(int(port)), "--remote-root", remote_root, "--wait", str(wait), "--min-free-gb", str(min_free_gb), "--package-output", package_output]
    if model_type != "auto":
        sync_cmd += ["--model-name", model_type]
        run_cmd_preview += ["--model-name", model_type]
        deploy_cmd += ["--type", model_type]
    if input_path.strip():
        deploy_cmd += ["--input", input_path.strip()]
    if json_path.strip():
        deploy_cmd += ["--json", json_path.strip()]
    run_cmd_preview += ["--force-convert" if force_convert else "--no-force-convert"]
    deploy_cmd += ["--force-convert" if force_convert else "--no-force-convert"]

    st.markdown("#### 📦 本地打包")
    render_command_preview(base_package_cmd())
    if st.button("📦 Package 模型", type="primary"):
        if not board_model or not abs_path(board_model).exists():
            st.error("模型文件不存在。")
        else:
            with st.spinner("正在打包..."):
                code, output = run_cmd(base_package_cmd(), timeout=300)
                save_result("package", code, output)
                st.session_state["package_generated"] = code == 0 and abs_path(package_output).exists()
    show_saved_result("package", "edgeai package")
    if st.session_state.get("package_generated") or abs_path(package_output).exists():
        pkg = abs_path(package_output)
        st.success(f"✓ 部署包: `{package_output}`")
        if pkg.exists():
            st.write([p.name for p in pkg.iterdir()])
            pr = load_json(pkg / "package_result.json")
            if pr:
                with st.expander("📋 package_result.json"):
                    st.json(pr)

    st.divider()
    st.markdown("#### 🚀 板端同步 / 运行")
    if host:
        if st.button("测试网络连通性（ping）", use_container_width=True):
            code, output = run_cmd(["ping", "-c", "1", "-W", "2", host], timeout=5)
            save_result("board_ping", code, output)
        show_saved_result("board_ping", "Board Ping")
    preview_tab1, preview_tab2, preview_tab3 = st.tabs(["Sync 命令", "Run 命令", "Deploy 命令"])
    with preview_tab1:
        render_command_preview(sync_cmd)
    with preview_tab2:
        render_command_preview(run_cmd_preview)
    with preview_tab3:
        render_command_preview(deploy_cmd)

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📤 Board Sync"):
            if not host:
                st.error("请填写香橙派 IP。")
            else:
                with st.spinner("同步中..."):
                    code, output = run_cmd(sync_cmd, timeout=300)
                    save_result("board_sync", code, output)
                    st.session_state["board_synced"] = code == 0
    with col2:
        if st.button("▶️ Board Run"):
            if not host:
                st.error("请填写香橙派 IP。")
            else:
                with st.spinner("远程运行中..."):
                    code, output = run_cmd(run_cmd_preview, timeout=600)
                    save_result("board_run", code, output)
                    st.session_state["board_ran"] = code == 0
    with col3:
        if st.button("⚡ 一键 Board Deploy", type="primary"):
            if not host:
                st.error("请填写香橙派 IP。")
            elif not board_model or not abs_path(board_model).exists():
                st.error("模型文件不存在。")
            else:
                with st.spinner("一键部署中，耐心等待..."):
                    code, output = run_cmd(deploy_cmd, timeout=900)
                    save_result("board_deploy", code, output)
                    st.session_state["board_deployed"] = code == 0
    show_saved_result("board_sync", "Board Sync")
    show_saved_result("board_run", "Board Run")
    show_saved_result("board_deploy", "Board Deploy")

    if abs_path(package_output).exists():
        with st.expander("📁 部署包与板端结果", expanded=True):
            render_package_preview(package_output)


# ═══════════════════════════════════════════
#  Page 6: Docker
# ═══════════════════════════════════════════

def render_docker_tab() -> None:
    st.markdown("### Docker 交付验证")
    st.caption("构建可交付镜像，并在容器中验证 CLI、ONNX 检查与 QEMU 部署入口。")

    d1, d2 = st.columns([1, 1])
    with d1:
        tag = st.text_input("镜像 tag", value="edgeai-deploykit:deploy")
        base_image = st.text_input("基础镜像", value="openeuler/openeuler:24.03-lts", help="Docker Hub 慢时可替换为 hub.oepkgs.net/openeuler/openeuler:24.03-lts")
    with d2:
        dockerfile = st.text_input("Dockerfile", value="docker/Dockerfile.deploy")
        progress_plain = st.checkbox("使用 --progress=plain", value=True)

    build_cmd = ["docker", "build"]
    if progress_plain:
        build_cmd.append("--progress=plain")
    build_cmd += ["--build-arg", f"BASE_IMAGE={base_image}", "-f", dockerfile, "-t", tag, "."]

    st.markdown("#### 构建镜像")
    render_command_preview(build_cmd)
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("拉取基础镜像", use_container_width=True):
            with st.spinner("正在拉取基础镜像..."):
                code, output = run_cmd(["docker", "pull", base_image], timeout=1800)
                save_result("docker_pull", code, output)
    with c2:
        if st.button("构建 Docker 镜像", type="primary", use_container_width=True):
            with st.spinner("Docker build 可能需要较长时间..."):
                code, output = run_cmd(build_cmd, timeout=3600)
                save_result("docker_build", code, output)
    with c3:
        if st.button("列出本地镜像", use_container_width=True):
            code, output = run_cmd(["docker", "images"], timeout=30)
            save_result("docker_images", code, output)
    show_saved_result("docker_pull", "Docker Pull")
    show_saved_result("docker_build", "Docker Build")
    show_saved_result("docker_images", "Docker Images")

    st.divider()
    st.markdown("#### 容器内 CLI 验证")
    mounted_root = st.text_input("挂载工程目录", value=str(PROJECT_ROOT))
    verify_model = st.text_input("容器内验证模型", value=st.session_state.get("model_path", "models/zoo/mnist/model.onnx"))
    verify_cmd = [
        "docker", "run", "--rm",
        "-v", f"{mounted_root}:/workspace",
        tag,
        "bash", "-lc",
        f"cd /workspace && pip3 install -e . --no-build-isolation && edgeai --help && edgeai check --model {verify_model}",
    ]
    render_command_preview(verify_cmd)
    if st.button("运行容器验证", use_container_width=True):
        with st.spinner("正在容器中验证 CLI..."):
            code, output = run_cmd(verify_cmd, timeout=600)
            save_result("docker_verify", code, output)
    show_saved_result("docker_verify", "Docker Verify")

    st.divider()
    st.markdown("#### Docker + QEMU")
    dq_model = st.text_input("QEMU 模型", value=verify_model, key="docker_qemu_model")
    qemu_dir = st.text_input("QEMU 目录", value="/root/qemu-5.0.0")
    initramfs = st.text_input("Initramfs", value="/root/initramfs.cpio", key="docker_initramfs")
    toolchain_dir = st.text_input("交叉编译工具链目录", value="/root/tools/gcc-linaro-7.5.0-2019.12-x86_64_aarch64-linux-gnu")
    docker_qemu_cmd = [
        "edgeai", "docker-run-qemu",
        "--model", dq_model,
        "--tag", tag,
        "--qemu-dir", qemu_dir,
        "--initramfs", initramfs,
        "--toolchain-dir", toolchain_dir,
        "--memory", "1024M",
    ]
    render_command_preview(docker_qemu_cmd)
    if st.button("运行 docker-run-qemu", use_container_width=True):
        with st.spinner("正在运行 Docker QEMU 验证..."):
            code, output = run_cmd(docker_qemu_cmd, timeout=900)
            save_result("docker_qemu", code, output)
    show_saved_result("docker_qemu", "Docker QEMU")


# ═══════════════════════════════════════════
#  Page 7: report center
# ═══════════════════════════════════════════

def render_report_center_tab() -> None:
    st.markdown("### 📊 报告中心")
    st.caption("汇总矩阵、生成模型报告与 PC/AIPro 对比报告。")

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📐 生成 Matrix", use_container_width=True):
            with st.spinner():
                code, output = run_cmd(["edgeai", "matrix"], timeout=120)
                save_result("matrix", code, output)
    with col2:
        if st.button("📋 生成 Matrix 报告", use_container_width=True):
            with st.spinner():
                code, output = run_cmd(["edgeai", "matrix-report"], timeout=120)
                save_result("matrix_report", code, output)
    with col3:
        if st.button("📊 生成 PC/AIPro 对比", use_container_width=True):
            with st.spinner():
                code, output = run_cmd(["edgeai", "pc-aipro-report"], timeout=120)
                save_result("pc_aipro_report", code, output)
    show_saved_result("matrix", "Matrix")
    show_saved_result("matrix_report", "Matrix Report")
    show_saved_result("pc_aipro_report", "PC/AIPro Report")

    st.divider()
    st.markdown("#### 📐 matrix.json")
    if MATRIX_JSON.exists():
        matrix = load_json(MATRIX_JSON)
        if isinstance(matrix, list):
            render_matrix_status_table(matrix)
            with st.expander("查看完整 matrix.json"):
                st.dataframe(pd.DataFrame(matrix), use_container_width=True, hide_index=True)
                render_file_download(MATRIX_JSON, "下载 matrix.json")
        else:
            st.json(matrix)
    else:
        st.info("暂无 `outputs/model_matrix/matrix.json`，请先执行「生成 Matrix」。")

    st.divider()
    st.markdown("#### 📄 已生成报告")
    reports = [
        ("模型矩阵 Markdown", REPORTS_DIR / "model_matrix.md"),
        ("模型矩阵 HTML", REPORTS_DIR / "model_matrix.html"),
        ("PC/AIPro Markdown", REPORTS_DIR / "pc_aipro_compare.md"),
        ("PC/AIPro HTML", REPORTS_DIR / "pc_aipro_compare.html"),
    ]
    for title, path in reports:
        if path.exists():
            if path.suffix == ".md":
                with st.expander(f"📄 {title}"):
                    st.markdown(load_text(path, max_chars=50000))
                    render_file_download(path)
            else:
                st.success(f"✓ {title}: `{rel(path)}`")
                render_file_download(path)
        else:
            st.caption(f"○ {title}: 未生成")


# ═══════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════

def main() -> None:
    st.set_page_config(page_title="EdgeAI Console", page_icon="⚡", layout="wide")

    # Inject premium, low-saturation theme
    st.markdown(PREMIUM_CSS, unsafe_allow_html=True)

    ensure_dirs()
    render_sidebar()

    # ── Header ──
    st.markdown(
        """
        <div class="edge-header">
          <div class="edge-kicker">Edge AI Deployment Workbench</div>
          <div class="edge-title">EdgeAI-DeployKit 控制台</div>
          <div class="edge-subtitle">从 ONNX 检查、量化与 Benchmark，到 QEMU/ARM64 验证、Docker 交付和香橙派 AIPro 板端部署，把边缘 AI 模型交付流程收束到一个稳定、清晰的工程驾驶舱。</div>
          <div class="edge-tag-row">
            <span class="edge-tag">ONNX Runtime</span>
            <span class="edge-tag">ATC → OM</span>
            <span class="edge-tag">QEMU ARM64</span>
            <span class="edge-tag">OrangePi AIPro</span>
            <span class="edge-tag">Matrix Report</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Runtime status strip ──
    components.html(CLOCK_HTML, height=78)

    st.divider()

    tab0, tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "总览",
        "🧠 模型选择",
        "🔍 Check / Quantize",
        "⚡ Benchmark / Report",
        "🖥️ ORT / QEMU",
        "🍊 香橙派 AIPro",
        "Docker",
        "📊 报告中心",
    ])
    with tab0:
        render_overview_tab()
    with tab1:
        render_model_tab()
    with tab2:
        render_check_quantize_tab()
    with tab3:
        render_benchmark_tab()
    with tab4:
        render_ort_qemu_tab()
    with tab5:
        render_board_tab()
    with tab6:
        render_docker_tab()
    with tab7:
        render_report_center_tab()


if __name__ == "__main__":
    main()


# -*- coding: utf-8 -*-
"""
Plexus Vagtplan
Lavet af Fabian Salvatore
"""
import streamlit as st
import json, os, calendar, random
from datetime import date, datetime, timedelta

VERSION     = date.today().strftime("%d.%m.%Y")
DATA_FILE   = "plexus_data.json"
VAGTDAG_IDX = {0, 1, 2, 6}

DAG_KORT  = {0:"Man",1:"Tirs",2:"Ons",3:"Tor",4:"Fre",5:"Lør",6:"Søn"}
DAG_LANG  = {0:"Mandag",1:"Tirsdag",2:"Onsdag",3:"Torsdag",
             4:"Fredag",5:"Lørdag",6:"Søndag"}
MÅNEDER   = ["","Januar","Februar","Marts","April","Maj","Juni",
             "Juli","August","September","Oktober","November","December"]
MÅN_GEN   = ["","januar","februar","marts","april","maj","juni",
             "juli","august","september","oktober","november","december"]

OPEN="open"; CLOSED="closed"; ACTIVITY="activity"
SETUP_CYCLE = {OPEN:CLOSED, CLOSED:OPEN}
SETUP_STYLE = {
    OPEN:   ("#c8e6c9","#43a047","#1b5e20","🟢","Åben"),
    CLOSED: ("#ffcdd2","#e53935","#b71c1c","🔴","Lukket"),
}
PREF_CYCLE  = {"":"sikker","sikker":"måske","måske":""}
PREF_STYLE  = {
    "":       ("#f8f9fa","#dee2e6","#555","⬜","Ikke valgt"),
    "sikker": ("#c8e6c9","#43a047","#1b5e20","✅","Ja"),
    "måske":  ("#fff9c4","#fbc02d","#6d4c00","🟡","Måske"),
}

CSS = """
<style>
.block-container{padding-top:1.2rem !important}
div[data-testid="stMetric"]{
    background:linear-gradient(135deg,#f0f9ff,#e8f5e9);
    border-radius:12px;padding:14px 18px;border:1px solid #e0e0e0}
div[data-testid="stMetric"] label{font-size:12px !important;color:#607d8b !important}
div[data-testid="stMetric"] [data-testid="stMetricValue"]{
    font-size:28px !important;font-weight:800 !important;color:#1a237e !important}
div[data-testid="stTabs"] button[data-baseweb="tab"]{
    font-size:14px !important;font-weight:600 !important;padding:8px 18px !important}
.stButton>button{border-radius:10px !important;font-weight:500 !important}
.stButton>button[kind="primary"]{
    background:linear-gradient(135deg,#1565c0,#0d47a1) !important;
    border:none !important;color:white !important}

/* ── Mørkt tema (dark mode) ────────────────────────────────────────────────── */
html[data-theme="dark"] div[data-testid="stMetric"]{
    background:linear-gradient(135deg,#0d2137,#0d2618) !important;
    border-color:#2a3a4a !important}
html[data-theme="dark"] div[data-testid="stMetric"] label{
    color:#7fa8c0 !important}
html[data-theme="dark"] div[data-testid="stMetric"] [data-testid="stMetricValue"]{
    color:#e8f5e9 !important}
html[data-theme="dark"] div[data-testid="stMetric"] [data-testid="stMetricDelta"]{
    color:#90caf9 !important}

/* Fallback via prefers-color-scheme hvis data-theme ikke sættes */
@media (prefers-color-scheme: dark) {
    div[data-testid="stMetric"]{
        background:linear-gradient(135deg,#0d2137,#0d2618) !important;
        border-color:#2a3a4a !important}
    div[data-testid="stMetric"] label{color:#7fa8c0 !important}
    div[data-testid="stMetric"] [data-testid="stMetricValue"]{color:#e8f5e9 !important}
    div[data-testid="stMetric"] [data-testid="stMetricDelta"]{color:#90caf9 !important}
}

/* ── Kalender-grid: fjern alle gaps/padding i hele kolonne-hierarkiet ──────── */
div[data-testid="stHorizontalBlock"]:has(.cal-overlay-cell),
div[data-testid="stHorizontalBlock"]:has(.plexus-cell-marker),
div[data-testid="stHorizontalBlock"]:has(.plexus-grey-cell),
div[data-testid="stHorizontalBlock"]:has(.plexus-dim-cell),
div[data-testid="stHorizontalBlock"]:has(.plexus-cal-header) {
    gap:0 !important; margin:0 !important; padding:0 !important}
div[data-testid="stHorizontalBlock"]:has(.cal-overlay-cell) > div[data-testid="column"],
div[data-testid="stHorizontalBlock"]:has(.plexus-cell-marker) > div[data-testid="column"],
div[data-testid="stHorizontalBlock"]:has(.plexus-grey-cell) > div[data-testid="column"],
div[data-testid="stHorizontalBlock"]:has(.plexus-dim-cell)  > div[data-testid="column"],
div[data-testid="stHorizontalBlock"]:has(.plexus-cal-header)> div[data-testid="column"] {
    padding:0 !important; margin:0 !important; min-width:0 !important}
div[data-testid="stHorizontalBlock"]:has(.cal-overlay-cell) > div[data-testid="column"] > div[data-testid="stVerticalBlock"],
div[data-testid="stHorizontalBlock"]:has(.plexus-cell-marker) > div[data-testid="column"] > div[data-testid="stVerticalBlock"],
div[data-testid="stHorizontalBlock"]:has(.plexus-grey-cell) > div[data-testid="column"] > div[data-testid="stVerticalBlock"],
div[data-testid="stHorizontalBlock"]:has(.plexus-dim-cell)  > div[data-testid="column"] > div[data-testid="stVerticalBlock"],
div[data-testid="stHorizontalBlock"]:has(.plexus-cal-header)> div[data-testid="column"] > div[data-testid="stVerticalBlock"] {
    gap:0 !important; padding:0 !important}
div[data-testid="stHorizontalBlock"]:has(.cal-overlay-cell) div[data-testid="element-container"],
div[data-testid="stHorizontalBlock"]:has(.plexus-cell-marker) div[data-testid="element-container"],
div[data-testid="stHorizontalBlock"]:has(.plexus-grey-cell) div[data-testid="element-container"],
div[data-testid="stHorizontalBlock"]:has(.plexus-dim-cell)  div[data-testid="element-container"],
div[data-testid="stHorizontalBlock"]:has(.plexus-cal-header)div[data-testid="element-container"] {
    margin:0 !important; padding:0 !important}
div[data-testid="stHorizontalBlock"]:has(.cal-overlay-cell) div[data-testid="stMarkdownContainer"],
div[data-testid="stHorizontalBlock"]:has(.plexus-cell-marker) div[data-testid="stMarkdownContainer"],
div[data-testid="stHorizontalBlock"]:has(.plexus-grey-cell) div[data-testid="stMarkdownContainer"],
div[data-testid="stHorizontalBlock"]:has(.plexus-dim-cell)  div[data-testid="stMarkdownContainer"],
div[data-testid="stHorizontalBlock"]:has(.plexus-cal-header)div[data-testid="stMarkdownContainer"] {
    margin:0 !important; padding:0 !important}

/* ── Kalender-celler som knapper ─────────────────────────────────────────── */
/* Marker-div er usynlig; CSS bruger den til at style den efterfølgende knap */
.plexus-cell-marker{display:none}
div[data-testid="element-container"]:has(.plexus-cell-marker)
  + div[data-testid="element-container"] div[data-testid="stButton"] > button {
    height:72px !important; width:100% !important;
    text-align:left !important; padding:5px 6px !important;
    white-space:pre-line !important; border-radius:0 !important;
    font-size:12px !important; line-height:1.3 !important;
    font-weight:500 !important; margin:0 !important;
    transition:filter .12s !important; cursor:pointer !important;
    display:block !important}
div[data-testid="element-container"]:has(.plexus-cell-marker)
  + div[data-testid="element-container"] div[data-testid="stButton"] > button:hover {
    filter:brightness(0.90) !important}
/* Setup: OPEN */
div[data-testid="element-container"]:has(.plexus-cell-open)
  + div[data-testid="element-container"] div[data-testid="stButton"] > button {
    background:#c8e6c9 !important; color:#1b5e20 !important;
    border:1px solid #43a047 !important; border-top:3px solid #43a047 !important}
/* Setup: CLOSED */
div[data-testid="element-container"]:has(.plexus-cell-closed-s)
  + div[data-testid="element-container"] div[data-testid="stButton"] > button {
    background:#ffcdd2 !important; color:#b71c1c !important;
    border:1px solid #e53935 !important; border-top:3px solid #e53935 !important}
/* Pref: ikke valgt */
div[data-testid="element-container"]:has(.plexus-cell-pref-none)
  + div[data-testid="element-container"] div[data-testid="stButton"] > button {
    background:#f8f9fa !important; color:#555 !important;
    border:1px solid #dee2e6 !important; border-top:3px solid #dee2e6 !important}
/* Pref: sikker/ja */
div[data-testid="element-container"]:has(.plexus-cell-pref-ja)
  + div[data-testid="element-container"] div[data-testid="stButton"] > button {
    background:#c8e6c9 !important; color:#1b5e20 !important;
    border:1px solid #43a047 !important; border-top:3px solid #43a047 !important}
/* Pref: måske */
div[data-testid="element-container"]:has(.plexus-cell-pref-maybe)
  + div[data-testid="element-container"] div[data-testid="stButton"] > button {
    background:#fff9c4 !important; color:#6d4c00 !important;
    border:1px solid #fbc02d !important; border-top:3px solid #fbc02d !important}

/* ── Kalender-wrapper: ydre ramme & afrunding via st.container() ────────── */
.plexus-cal-boundary {display:none}
div[data-testid="stVerticalBlock"]:has(> div[data-testid="element-container"] > div[data-testid="stMarkdownContainer"] > .plexus-cal-boundary) {
    border:1px solid #e0e0e0 !important;
    border-radius:12px !important;
    overflow:hidden !important;
    gap:0 !important;
    padding:0 !important;
    margin-bottom:16px !important}

/* ── Svag-rød (danger/warn) knapper ──────────────────────────────────────── */
div[data-testid="element-container"]:has(.plexus-warn-btn)   + div[data-testid="element-container"] > div[data-testid="stButton"] > button,
div[data-testid="element-container"]:has(.plexus-danger-btn) + div[data-testid="element-container"] > div[data-testid="stButton"] > button {
    background:#fff0f0 !important;
    color:#c62828 !important;
    border:1px solid #ef9a9a !important}
div[data-testid="element-container"]:has(.plexus-warn-btn)   + div[data-testid="element-container"] > div[data-testid="stButton"] > button:hover,
div[data-testid="element-container"]:has(.plexus-danger-btn) + div[data-testid="element-container"] > div[data-testid="stButton"] > button:hover {
    background:#ffcdd2 !important;
    border-color:#e53935 !important}

/* Grå lukket-celler (ikke-valgbare vagtdage) */
html[data-theme="dark"] .plexus-grey-cell{
    background:#252525 !important;border-color:#383838 !important;color:#555 !important}
html[data-theme="dark"] .plexus-grey-cell > div{color:#555 !important}

/* Dæmpede ikke-vagtdage */
html[data-theme="dark"] .plexus-dim-cell{
    background:#1c1c1c !important;border-color:#262626 !important;color:#404040 !important}
html[data-theme="dark"] .plexus-dim-cell > div{color:#404040 !important}

/* HTML-resultat-kalender — åbne/aktivitetsdage */
html[data-theme="dark"] .plexus-calendar td{
    border-color:#333 !important}
html[data-theme="dark"] .plexus-calendar thead th{
    background:#0d1a2e !important;border-color:#1a2a3e !important;color:#5a9fd4 !important}
html[data-theme="dark"] .plexus-calendar .plexus-cal-empty{
    background:#161616 !important;border-color:#222 !important}
html[data-theme="dark"] .plexus-calendar .plexus-cal-planned-closed{
    background:#202020 !important;border-color:#303030 !important}
html[data-theme="dark"] .plexus-calendar .plexus-cal-planned-closed div{
    color:#555 !important}
/* Tving læsbare tekstfarver i alle kalender-celler ved mørkt tema */
html[data-theme="dark"] .plexus-calendar td div{
    color:inherit}
html[data-theme="dark"] .plexus-calendar td[style*="background:#e8f5e9"] div,
html[data-theme="dark"] .plexus-calendar td[style*="background:#dbeafe"] div,
html[data-theme="dark"] .plexus-calendar td[style*="background:#ffebee"] div{
    color:#111 !important}
html[data-theme="dark"] .plexus-calendar td[style*="background:#e8f5e9"]{
    background:#1b3a1f !important}
html[data-theme="dark"] .plexus-calendar td[style*="background:#dbeafe"]{
    background:#0d2347 !important}
html[data-theme="dark"] .plexus-calendar td[style*="background:#ffebee"]{
    background:#3a1010 !important}
html[data-theme="dark"] .plexus-calendar td[style*="background:#e8f5e9"] div,
html[data-theme="dark"] .plexus-calendar td[style*="background:#1b3a1f"] div{
    color:#a5d6a7 !important}
html[data-theme="dark"] .plexus-calendar td[style*="background:#dbeafe"] div,
html[data-theme="dark"] .plexus-calendar td[style*="background:#0d2347"] div{
    color:#90caf9 !important}
html[data-theme="dark"] .plexus-calendar td[style*="background:#ffebee"] div,
html[data-theme="dark"] .plexus-calendar td[style*="background:#3a1010"] div{
    color:#ef9a9a !important}
</style>
"""

# CSS til usynlig overlay-knap der dækker hele datocellen
OVERLAY_CAL_CSS = """
<style>
div[data-testid="stMarkdownContainer"]:has(.cal-overlay-cell)
  + div[data-testid="stButton"] {
    margin-top: -72px !important;
    height: 72px !important;
    position: relative;
    z-index: 10;
}
div[data-testid="stMarkdownContainer"]:has(.cal-overlay-cell)
  + div[data-testid="stButton"] > button {
    height: 72px !important;
    width: 100% !important;
    opacity: 0 !important;
    cursor: pointer !important;
    border: none !important;
    background: transparent !important;
    margin: 0 !important;
    padding: 0 !important;
    display: block !important;
    border-radius: 0 !important;
}
/* Hover-glow på cellen: viser at hele fladen er klikbar */
.cal-overlay-cell:hover {
    filter: brightness(0.93) !important;
    cursor: pointer !important;
}
</style>
"""

# ── Persistent storage via Supabase REST API ─────────────────────────────────
#
# OPSÆTNING:
#  1. Opret gratis projekt på supabase.com
#  2. Opret tabel "app_data" med kolonner:
#       record_key  (text, primary key)
#       value       (text)
#  3. Tilføj til Streamlit Cloud → App settings → Secrets:
#
#       [supabase]
#       url = "https://xxxx.supabase.co"
#       key = "din-anon-key"
#
# Uden secrets bruges lokal JSON-fil (velegnet til lokal udvikling).
# ─────────────────────────────────────────────────────────────────────────────

def _use_supabase() -> bool:
    """Returnerer True hvis Supabase-credentials er konfigureret."""
    try:
        return "supabase" in st.secrets
    except Exception:
        return False


def _sb_headers() -> dict:
    key = st.secrets["supabase"]["key"]
    return {
        "apikey":        key,
        "Authorization": f"Bearer {key}",
        "Content-Type":  "application/json",
        "Prefer":        "return=minimal",
    }


def _sb_url(path: str = "") -> str:
    base = st.secrets["supabase"]["url"].rstrip("/")
    return f"{base}/rest/v1/app_data{path}"


def _empty_data() -> dict:
    return {"volunteers": {}, "monthly_config": {}, "preferences": {},
            "assignments": {}, "admin_password": "plexus2024", "next_id": 1}


def load() -> dict:
    """Indlæs data — fra Supabase hvis konfigureret, ellers lokal JSON."""
    import requests
    raw = {}
    if _use_supabase():
        try:
            r = requests.get(
                _sb_url(),
                headers=_sb_headers(),
                params={"record_key": "eq.plexus", "select": "value"},
                timeout=10,
            )
            r.raise_for_status()
            rows = r.json()
            if rows:
                raw = json.loads(rows[0]["value"])
        except Exception as e:
            st.error(f"⚠️ Kunne ikke hente data fra Supabase: {e}")
            raw = {}
    elif os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except (json.JSONDecodeError, OSError):
            st.error("⚠️ Datafilen er beskadiget. Starter med tomt datasæt.")
            raw = {}

    defaults = _empty_data()
    for k, v in defaults.items():
        raw.setdefault(k, v)
    return raw


def save(data: dict):
    """Gem data — til Supabase hvis konfigureret, ellers lokal JSON."""
    import requests
    if _use_supabase():
        try:
            headers = _sb_headers()
            headers["Prefer"] = "resolution=merge-duplicates"
            r = requests.post(
                _sb_url(),
                headers=headers,
                json={"record_key": "plexus",
                      "value": json.dumps(data, ensure_ascii=False)},
                timeout=10,
            )
            r.raise_for_status()
        except Exception as e:
            st.error(f"❌ Kunne ikke gemme data til Supabase: {e}")
    else:
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except OSError as e:
            st.error(f"❌ Kunne ikke gemme data: {e}")


def mk(y, m) -> str:
    return f"{y}-{m:02d}"


def mk_label(k) -> str:
    try:
        y, m = k.split("-")
        return f"{MÅNEDER[int(m)]} {y}"
    except (ValueError, IndexError):
        return k


def full_dato(d_str: str) -> str:
    try:
        d = date.fromisoformat(d_str)
        return f"{DAG_LANG[d.weekday()]} den {d.day}. {MÅN_GEN[d.month]}"
    except (ValueError, KeyError):
        return d_str


def fmt_dansk(d: date) -> str:
    """Dansk datoformat: dd-mm-yyyy."""
    return f"{d.day:02d}-{d.month:02d}-{d.year}"


def fmt_dansk_lang(d: date) -> str:
    """Dansk langt format: 5. marts 2025."""
    return f"{d.day}. {MÅN_GEN[d.month]} {d.year}"


def default_date_types(y: int, m: int) -> dict:
    n = calendar.monthrange(y, m)[1]
    return {date(y, m, d).isoformat():
            (OPEN if date(y, m, d).weekday() in VAGTDAG_IDX else CLOSED)
            for d in range(1, n + 1)}


def get_date_types(cfg: dict, y: int, m: int) -> dict:
    if "date_types" in cfg:
        return cfg["date_types"]
    return {d: OPEN for d in cfg.get("dates", [])}


def default_deadline(y: int, m: int) -> date:
    """Standard: 3 dage inden måneden starter."""
    return date(y, m, 1) - timedelta(days=3)


def default_setup_month(data: dict) -> tuple:
    """
    Standard for Måneds-opsætning:
    Indeværende måned — medmindre den er frigivet, så næstkommende ikke-frigivne.
    """
    now = datetime.now()
    y, m = now.year, now.month
    for _ in range(24):
        mkey = mk(y, m)
        if not data["monthly_config"].get(mkey, {}).get("released", False):
            return y, m
        m += 1
        if m > 12:
            m = 1
            y += 1
    return now.year, now.month


def latest_released_month(data: dict) -> str | None:
    """Returnerer den nyeste frigivne måned (til Vagttildeling-tab)."""
    frigivne = sorted(k for k, c in data["monthly_config"].items()
                      if c.get("released", False))
    return frigivne[-1] if frigivne else None


def latest_assigned_month(data: dict) -> str | None:
    """Returnerer den seneste måned med tildelte vagter (til Resultater-tab)."""
    tildelte = sorted(data.get("assignments", {}).keys())
    return tildelte[-1] if tildelte else None


# ── Kalender-hjælpere ─────────────────────────────────────────────────────────
def _dag_header():
    """Tabelagtig ugedag-header — matcher HTML-kalenderens thead."""
    cols = st.columns(7)
    for i in range(7):
        cols[i].markdown(
            f'<div class="plexus-cal-header" style="text-align:center;font-size:12px;font-weight:700;'
            f'padding:10px 4px;letter-spacing:0.5px;'
            f'background:#f0f7ff;color:#1565c0;'
            f'border:1px solid #e0e0e0;border-bottom:3px solid #1565c0;margin-bottom:-1px">'
            f'{DAG_LANG[i]}</div>', unsafe_allow_html=True)


def _colored_cell(bg, border, text, dag, day, maan, status, overlay=False):
    cls = ' class="cal-overlay-cell"' if overlay else ''
    st.markdown(
        f'<div{cls} style="background:{bg};border:1px solid {border};'
        f'border-top:3px solid {border};'
        f'padding:5px 6px;vertical-align:top;height:72px;box-sizing:border-box;'
        f'display:flex;flex-direction:column;gap:0">'
        f'<div style="display:flex;justify-content:space-between;align-items:center">'
        f'<span style="font-size:9px;font-weight:700;color:{text};'
        f'text-transform:uppercase;letter-spacing:0.3px;opacity:0.85">{dag}</span>'
        f'<span style="font-size:9px;font-weight:600;color:{text};white-space:nowrap;opacity:0.85">{status}</span>'
        f'</div>'
        f'<div style="font-size:20px;font-weight:900;color:{text};line-height:1.15;margin-top:1px">{day}</div>'
        f'<div style="font-size:9px;color:{text};opacity:0.7;margin-top:1px">{maan}</div>'
        f'</div>', unsafe_allow_html=True)


def _grey_cell_nobutton(dag, day, maan, label=""):
    """Grå celle UDEN knap — vises for ikke-valgbare dage."""
    st.markdown(
        f'<div class="plexus-grey-cell" style="background:#f5f5f5;border:1px solid #e0e0e0;'
        f'padding:5px 6px;vertical-align:top;'
        f'height:72px;box-sizing:border-box;display:flex;flex-direction:column;gap:0;'
        f'color:#bbb;opacity:0.6">'
        f'<div style="display:flex;justify-content:space-between;align-items:center">'
        f'<span style="font-size:9px;font-weight:700;text-transform:uppercase">{dag}</span>'
        f'<span style="font-size:9px;font-weight:600;white-space:nowrap">{label}</span>'
        f'</div>'
        f'<div style="font-size:20px;font-weight:900;line-height:1.15;margin-top:1px">{day}</div>'
        f'<div style="font-size:9px;opacity:0.8;margin-top:1px">{maan}</div>'
        f'</div>', unsafe_allow_html=True)


def _non_vagtdag_cell(dag, day, maan):
    """Meget lys celle for dage der ikke er vagtdage (Tor/Fre/Lør)."""
    st.markdown(
        f'<div class="plexus-dim-cell" style="background:#fafafa;border:1px solid #f0f0f0;'
        f'padding:8px 5px;vertical-align:top;'
        f'min-height:90px;color:#ddd">'
        f'<div style="font-size:10px;font-weight:700;text-transform:uppercase;'
        f'letter-spacing:0.4px">{dag}</div>'
        f'<div style="font-size:22px;font-weight:900;line-height:1">{day}</div>'
        f'<div style="font-size:9px;opacity:0.8">{maan}</div>'
        f'</div>', unsafe_allow_html=True)


def _empty_cell():
    st.markdown('<div style="height:72px;box-sizing:border-box"></div>', unsafe_allow_html=True)


# ── Fordelingsalgoritme ───────────────────────────────────────────────────────
def auto_assign(data: dict, mkey: str, locked_shifts: dict | None = None) -> dict:
    """
    FIRE-FASE VAGTTILDELING
    ═══════════════════════

    Hård begrænsning:
      Frivillige der HAR indsendt ønsker må KUN tildeles dage de explicit har sagt
      ja eller måske til. De tildeles ALDRIG dage uden for egne indsendte datoer.
      Frivillige der IKKE har indsendt ønsker kan tildeles alle åbne dage.

    Prioritetsrækkefølge (højest → lavest):
      1.  Låste vagter (admin) indsættes altid først
      2.  Flest mulige åbningsdage (≥ min_per frivillige)
      3.  Gap-spredning: åbn én dag i hvert lukket interval før to i samme
      4.  Hverdage (Man/Tirs/Ons) foretrækkes over søndage
      5.  Præference: Ja > Måske  (frivillige uden ønsker tildeles derefter)
      6.  Ligelig fordeling af vagter

    Faser:
      Fase 1 — Åbn dage med KUN ja-præferencer
      Fase 2 — Åbn resterende med ja + måske
      Fase 3 — Åbn resterende med alle (inkl. ingen ønsker)
      Fase 4 — Fordel resterende kvoter til åbne dage
    """
    cfg      = data["monthly_config"].get(mkey, {})
    y, m     = int(mkey[:4]), int(mkey[5:7])
    dt       = get_date_types(cfg, y, m)
    active_d = sorted(d for d, t in dt.items() if t in (OPEN, ACTIVITY))
    min_per  = max(1, int(cfg.get("min_per_shift", 3)))
    max_per  = max(min_per, int(cfg.get("max_per_shift", 3)))
    prefs_m  = data["preferences"].get(mkey, {})
    vols     = data["volunteers"]
    active   = [vid for vid, v in vols.items() if v.get("active", True)]
    random.shuffle(active)   # Tilfældig startrækkefølge sikrer variation ved genberegning

    if not active_d or not active:
        data["assignments"][mkey] = {
            "shifts": {}, "open": [], "closed": sorted(dt.keys()),
            "activity": [], "unmet_quota": {},
            "generated_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
        }
        return data

    # Frivillige der har indsendt ønsker (hård begrænsning — tildeles KUN på ja/måske dage)
    has_submitted: set = set(prefs_m.keys())

    # Præference-matrix: 2=sikker/ja, 1=måske, 0=ikke relevant for denne dag
    prio: dict = {
        vid: {
            d: (2 if prefs_m.get(vid, {}).get(d) == "sikker"
                else 1 if prefs_m.get(vid, {}).get(d) == "måske"
                else 0)
            for d in active_d
        }
        for vid in active
    }

    quota     = {vid: max(0, int(vols[vid].get("required_shifts", 2))) for vid in active}
    remaining = dict(quota)
    shifts: dict = {d: [] for d in active_d}
    day_obj: dict = {d: date.fromisoformat(d) for d in active_d}

    # ── Pre-populer låste vagter ─────────────────────────────────────────────
    if locked_shifts:
        for d, vids in locked_shifts.items():
            if d in shifts:
                for vid in vids:
                    if vid in active and vid not in shifts[d]:
                        shifts[d].append(vid)
                        remaining[vid] = max(0, remaining[vid] - 1)

    # ── Hjælpefunktioner ────────────────────────────────────────────────────

    def can_work(vid: str, d: str) -> bool:
        """
        Hård begrænsning:
        Frivillige MED indsendte ønsker → KUN dage de sagde ja eller måske til.
        Frivillige UDEN indsendte ønsker → alle aktive dage.
        """
        if vid in has_submitted:
            return prio[vid][d] > 0
        return True

    def pref_group(vid: str, d: str) -> int:
        """
        Sorteringsniveau. Lav = høj prioritet.
          0 = ja/sikker for denne dag
          1 = måske for denne dag
          2 = ingen indsendte ønsker (no-submitted) — tildeles sidst
        """
        if vid not in has_submitted:
            return 2   # ingen ønsker — laveste prioritet
        p = prio[vid][d]
        if p == 2: return 0   # ja
        if p == 1: return 1   # måske
        return 2               # burde aldrig nås pga. can_work-begrænsning

    def fraction_done(vid: str) -> float:
        """
        Andel af kvoten der allerede er tildelt (0.0–1.0).
        Lav andel = har fået mindst relativt → prioriteres højest for ligelig fordeling.
        """
        q = quota[vid]
        if q == 0:
            return 1.0
        return (q - remaining[vid]) / q

    def weekday_score(d: str) -> int:
        """0=hverdag (Man/Tirs/Ons), 1=søndag."""
        return 0 if day_obj[d].weekday() in {0, 1, 2} else 1

    def gap_run_length(d: str) -> int:
        """
        Antal sammenhængende lukkede active_d-dage i det interval d tilhører.
        Høj værdi = dag sidder midt i et langt lukket stræk → prioriteres
        højere, så algoritmen åbner én dag i hvert gap frem for at klumpe.
        """
        try:
            idx = active_d.index(d)
        except ValueError:
            return 0
        left = 0
        for i in range(idx - 1, -1, -1):
            if len(shifts[active_d[i]]) >= min_per:
                break
            left += 1
        right = 0
        for i in range(idx + 1, len(active_d)):
            if len(shifts[active_d[i]]) >= min_per:
                break
            right += 1
        return left + right + 1

    def eligible_open(vid: str, d: str, max_pref_group: int) -> bool:
        """
        Kan vid bruges til at åbne dag d i den givne fase?
        max_pref_group: 0=kun ja-folk, 1=ja+måske-folk, 2=alle inkl. ingen ønsker
        """
        if not can_work(vid, d):
            return False
        if vid in shifts[d] or remaining[vid] <= 0 or len(shifts[d]) >= max_per:
            return False
        return pref_group(vid, d) <= max_pref_group

    def fill_day(d: str, max_pref_group: int) -> bool:
        """
        Forsøg at åbne dag d op til min_per.
        Commit'er KUN hvis nok kandidater — spildes ingen kvoter ellers.
        Kandidater sorteres:
          1. Præference-gruppe (ja > måske > ingen)
          2. Lavest andel af kvote tildelt (ligelig fordeling)
          3. Flest absolutte vagter tilbage (tiebreaker)
        """
        if len(shifts[d]) >= min_per:
            return True
        cands = sorted(
            [v for v in active if eligible_open(v, d, max_pref_group)],
            key=lambda v: (pref_group(v, d), fraction_done(v), -remaining[v], random.random())
        )
        needed = min_per - len(shifts[d])
        if len(cands) < needed:
            return False
        for v in cands[:needed]:
            shifts[d].append(v)
            remaining[v] -= 1
        return True

    def day_sort_key(d: str) -> tuple:
        """
        Sortér lukkede dage:
          1. Længste gap-run FØRST (åbn bredt, ikke klumpet)
          2. Hverdag FREM FOR søndag
        """
        return (-gap_run_length(d), weekday_score(d), random.random())

    def try_open_all(max_pref_group: int):
        """
        Gentag åbning af lukkede dage til ingen fremskridt.
        Rækkefølge: longest-gap-first + hverdage først.
        """
        changed = True
        while changed:
            changed = False
            for d in sorted([d for d in active_d if len(shifts[d]) < min_per],
                            key=day_sort_key):
                before = len(shifts[d])
                if fill_day(d, max_pref_group) and before < min_per:
                    changed = True

    # ════════════════════════════════════════════════════════════════════════
    # FASE 1 — Åbn dage med KUN ja/sikker-frivillige
    # Hård begrænsning: submitted-folk kun på egne ja-dage
    # ════════════════════════════════════════════════════════════════════════
    try_open_all(max_pref_group=0)

    # ════════════════════════════════════════════════════════════════════════
    # FASE 2 — Åbn resterende dage: ja + måske
    # ════════════════════════════════════════════════════════════════════════
    try_open_all(max_pref_group=1)

    # ════════════════════════════════════════════════════════════════════════
    # FASE 3 — Åbn resterende dage: alle, inkl. ingen-ønsker-frivillige
    # ════════════════════════════════════════════════════════════════════════
    try_open_all(max_pref_group=2)

    # ════════════════════════════════════════════════════════════════════════
    # FASE 4 — Fordel resterende kvoter
    # Mål: ligelig fordeling (alle ~samme % af kvote) + spredning
    #
    # Vælg frivillig med LAVEST andel tildelt (fraction_done) FØRST.
    # For hver frivillig: foretrék åbne dage → hverdage → isolerede dage.
    # Hård begrænsning overholdes: submitted-folk kun på egne ja/måske-dage.
    # ════════════════════════════════════════════════════════════════════════
    total_rem = sum(remaining.values())
    for _ in range(total_rem * 2 + 1):
        vols_left = [v for v in active if remaining[v] > 0]
        if not vols_left:
            break
        # Prioritér den med lavest andel tildelt (mest "bagud" relativt til kvote)
        vols_left.sort(key=lambda v: (fraction_done(v), -remaining[v], random.random()))

        assigned = False
        for vid in vols_left:
            best_d     = None
            best_score = None

            for d in active_d:
                if not can_work(vid, d):
                    continue
                if vid in shifts[d] or len(shifts[d]) >= max_per:
                    continue

                is_open = len(shifts[d]) >= min_per
                if not is_open:
                    # Tjek om dagen stadig kan åbnes med tilgængelige folk
                    gap   = min_per - len(shifts[d])
                    avail = sum(1 for v in active
                                if can_work(v, d) and v not in shifts[d]
                                and remaining[v] > 0 and len(shifts[d]) < max_per)
                    if avail < gap:
                        continue

                opn     = 0 if is_open else 1          # åbne dage foretrækkes
                wday    = weekday_score(d)              # hverdage foretrækkes
                gap_pri = -gap_run_length(d) if not is_open else 0  # største gap
                pg      = pref_group(vid, d)            # ja > måske > ingen
                fill    = len(shifts[d])                # mindst fyldt

                score = (opn, wday, gap_pri, pg, fill)
                if best_score is None or score < best_score:
                    best_score = score
                    best_d = d

            if best_d is not None:
                shifts[best_d].append(vid)
                remaining[vid] -= 1
                assigned = True
                break

        if not assigned:
            break

    # ════════════════════════════════════════════════════════════════════════
    # KLASSIFICÉR OG GEM
    # ════════════════════════════════════════════════════════════════════════
    open_set  = {d for d in active_d if len(shifts[d]) >= min_per}
    open_d    = sorted(open_set)
    closed_d  = sorted(
        ({d for d in active_d if d not in open_set})
        | ({d for d, t in dt.items() if t == CLOSED})
    )
    open_shifts = {vid: sum(1 for d in open_set if vid in shifts[d]) for vid in active}
    unmet = {vid: quota[vid] - open_shifts[vid]
             for vid in active if open_shifts[vid] < quota[vid]}

    data["assignments"][mkey] = {
        "shifts":          {d: lst for d, lst in shifts.items()},
        "open":            open_d,
        "closed":          closed_d,
        "activity":        [],
        "configured_open": active_d,
        "unmet_quota":     unmet,
        "generated_at":    datetime.now().strftime("%d/%m/%Y %H:%M"),
    }
    return data


# ══════════════════════════════════════════════════════════════════════════════
#  STATISK HTML-KALENDER
# ══════════════════════════════════════════════════════════════════════════════
def _html_thead() -> str:
    cells = "".join(
        f'<th style="padding:10px 4px;font-size:12px;font-weight:700;'
        f'letter-spacing:0.5px;border:1px solid #e0e0e0;'
        f'background:#f0f7ff;color:#1565c0;'
        f'border-bottom:3px solid #1565c0">'
        f'{DAG_LANG[i]}</th>'
        for i in range(7))
    return f"<thead><tr>{cells}</tr></thead>"


def cal_html_resultater(mkey, shifts, open_days, closed_days, activity_days,
                        vols, highlight_vid=None, volunteer_view=False,
                        configured_open=None):
    """
    Rendrer HTML-kalender med vagttildelinger.

    Tre typer dage vises forskelligt:
      🟢/🔵  Åbningsdag    — nok frivillige (grøn/blå)
      🔴     For få        — planlagt åben, men ikke nok frivillige (rød)
      ⬜     Planlagt lukket — sat til CLOSED i opsætningen (neutral grå)

    volunteer_view=True: "for få"-dage skjuler navnelisten.
    configured_open: liste over dage der var sat til OPEN/ACTIVITY i opsætningen.
                     Bruges til at skelne "planlagt lukket" fra "for få frivillige".
    """
    try:
        y, m = int(mkey[:4]), int(mkey[5:7])
    except (ValueError, AttributeError):
        return "<p>Ugyldig månednøgle.</p>"

    open_set          = set(open_days)
    activity_set      = set(activity_days)
    configured_set    = set(configured_open) if configured_open else None

    rows = ""
    for week in calendar.monthcalendar(y, m):
        rows += "<tr>"
        for i, day in enumerate(week):
            if day == 0:
                rows += ('<td class="plexus-cal-empty" style="background:#fafafa;border:1px solid #ececec;'
                         'padding:6px;min-width:110px;height:130px;box-sizing:border-box"></td>')
                continue
            d_str = date(y, m, day).isoformat()

            # Bestem dagtype ud fra assignments-data (ikke ugedag)
            is_open   = d_str in open_set
            is_act    = d_str in activity_set
            in_shifts = d_str in shifts   # havde tildelinger (åben eller for få)

            # Er dagen overhovedet planlagt aktiv?
            if configured_set is not None:
                was_planned_open = d_str in configured_set
            else:
                # Fallback: hvis den har vagttildelinger eller er i open/closed
                was_planned_open = in_shifts

            if is_open:
                # ── Åbningsdag ───────────────────────────────────────
                if is_act:
                    bg, hdr, dot, status_txt = "#dbeafe", "#0d47a1", "🔵", "Aktivitet"
                else:
                    bg, hdr, dot, status_txt = "#e8f5e9", "#1b5e20", "🟢", "Åben"

                navne = [(v, vols[v]["name"]) for v in shifts.get(d_str, []) if v in vols]
                names_html = "".join(
                    f'<div style="font-size:11px;margin-top:2px;padding:1px 6px;'
                    f'border-radius:4px;'
                    f'background:{"#a5d6a7" if vid == highlight_vid else "#ffffffcc"};'
                    f'color:{"#1b5e20" if vid == highlight_vid else "#333"};'
                    f'font-weight:{"700" if vid == highlight_vid else "400"}">'
                    f'{"★ " if vid == highlight_vid else ""}{name}</div>'
                    for vid, name in navne
                )
                rows += (f'<td style="background:{bg};border:1px solid #ccc;'
                         f'padding:8px 6px;vertical-align:top;min-width:110px;height:130px;box-sizing:border-box">'
                         f'<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:2px">'
                         f'<span style="font-size:10px;font-weight:700;color:{hdr}">{DAG_LANG[i]}</span>'
                         f'<span style="font-size:10px;font-weight:600;color:{hdr};white-space:nowrap">{dot} {status_txt}</span>'
                         f'</div>'
                         f'<div style="font-size:22px;font-weight:900;color:{hdr};line-height:1.1">{day}</div>'
                         f'<div style="font-size:9px;color:{hdr};margin-bottom:4px">{MÅN_GEN[m]}</div>'
                         f'{names_html}</td>')

            elif was_planned_open:
                # ── For få frivillige (planlagt åben, men lukket) ────
                bg, hdr = "#ffebee", "#c62828"
                navne = [(v, vols[v]["name"]) for v in shifts.get(d_str, []) if v in vols]

                if volunteer_view:
                    # Frivillige ser ikke hvem der er tildelt, men får besked om årsagen
                    body_html = ('<div style="font-size:10px;color:#c62828;'
                                 'margin-top:4px;font-style:italic">Lukket – for få frivillige</div>')
                else:
                    # Admin ser tildelingerne (selv om dagen lukker)
                    body_html = (
                        '<div style="font-size:10px;color:#c62828;'
                        'margin-top:2px;font-style:italic">For få frivillige</div>'
                        + "".join(
                            f'<div style="font-size:10px;margin-top:2px;padding:1px 5px;'
                            f'border-radius:4px;background:#ffcdd2;color:#b71c1c">'
                            f'{name}</div>'
                            for _, name in navne
                        )
                    )
                rows += (f'<td style="background:{bg};border:1px solid #ef9a9a;'
                         f'padding:8px 6px;vertical-align:top;min-width:110px;height:130px;box-sizing:border-box">'
                         f'<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:2px">'
                         f'<span style="font-size:10px;font-weight:700;color:{hdr}">{DAG_LANG[i]}</span>'
                         f'<span style="font-size:10px;font-weight:600;color:{hdr};white-space:nowrap">🔴 Lukket</span>'
                         f'</div>'
                         f'<div style="font-size:22px;font-weight:900;color:{hdr};line-height:1.1">{day}</div>'
                         f'<div style="font-size:9px;color:{hdr};margin-bottom:4px">{MÅN_GEN[m]}</div>'
                         f'{body_html}</td>')

            else:
                # ── Planlagt lukket (sat til CLOSED i opsætningen) ───
                rows += (f'<td class="plexus-cal-planned-closed" style="background:#f5f5f5;border:1px solid #e0e0e0;'
                         f'padding:8px 6px;vertical-align:top;min-width:110px;height:130px;box-sizing:border-box;opacity:0.6">'
                         f'<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:2px">'
                         f'<span style="font-size:10px;font-weight:700;color:#9e9e9e">{DAG_LANG[i]}</span>'
                         f'<span style="font-size:10px;color:#bdbdbd;white-space:nowrap">📅 Lukket</span>'
                         f'</div>'
                         f'<div style="font-size:22px;font-weight:900;color:#bdbdbd;line-height:1.1">{day}</div>'
                         f'<div style="font-size:9px;color:#bdbdbd">{MÅN_GEN[m]}</div>'
                         f'</td>')

        rows += "</tr>"

    return (f'<div class="plexus-calendar" style="overflow-x:auto;border-radius:12px;border:1px solid #e0e0e0;overflow:hidden">'
            f'<table style="border-collapse:collapse;width:100%;table-layout:fixed">'
            + _html_thead() + f"<tbody>{rows}</tbody></table></div>")


# ══════════════════════════════════════════════════════════════════════════════
#  INTERAKTIVE KALENDERE
# ══════════════════════════════════════════════════════════════════════════════
def render_setup_kalender(mkey: str) -> dict:
    try:
        y, m = int(mkey[:4]), int(mkey[5:7])
    except (ValueError, AttributeError):
        st.error("Ugyldig månednøgle.")
        return {}

    sk = f"sc_{mkey}"
    if sk not in st.session_state:
        cfg = st.session_state.get(f"cfg_{mkey}", {})
        st.session_state[sk] = (dict(cfg["date_types"]) if "date_types" in cfg
                                 else default_date_types(y, m))

    with st.container():
      st.markdown('<div class="plexus-cal-boundary"></div>', unsafe_allow_html=True)
      _dag_header()
      for week in calendar.monthcalendar(y, m):
        cols = st.columns(7)
        for i, day in enumerate(week):
            with cols[i]:
                if day == 0:
                    _empty_cell()
                    continue
                d_str = date(y, m, day).isoformat()
                state = st.session_state[sk].get(d_str, CLOSED)
                if state not in SETUP_CYCLE:
                    state = CLOSED
                _, _, _, icon, lbl = SETUP_STYLE[state]
                next_s = SETUP_CYCLE[state]
                css_cls = "plexus-cell-open" if state == OPEN else "plexus-cell-closed-s"
                st.markdown(
                    f'<div class="plexus-cell-marker {css_cls}"></div>',
                    unsafe_allow_html=True)
                btn_lbl = f"{DAG_LANG[i][:3]}  {icon} {lbl}\n{day}. {MÅN_GEN[m][:3]}"
                if st.button(btn_lbl, key=f"sc_{mkey}_{d_str}",
                             use_container_width=True):
                    st.session_state[sk][d_str] = next_s
                    st.rerun()
    return dict(st.session_state[sk])


def render_pref_kalender(mkey: str, vid: str, date_types: dict, existing: dict) -> dict:
    """
    Desktop præference-kalender.
    Valgbarhed bestemmes KUN af opsætningens date_types — ikke ugedag.
    - OPEN / ACTIVITY → klikbar, farvet celle
    - CLOSED          → planlagt lukket, grå, ingen knap
    - Ingen config    → tom/neutral celle
    """
    try:
        y, m = int(mkey[:4]), int(mkey[5:7])
    except (ValueError, AttributeError):
        st.error("Ugyldig månednøgle.")
        return {}

    sk = f"vp_{mkey}_{vid}"
    if sk not in st.session_state:
        st.session_state[sk] = dict(existing)
    rel_set = {d for d, t in date_types.items() if t in (OPEN, ACTIVITY)}

    _PREF_CLS = {"": "plexus-cell-pref-none",
                  "sikker": "plexus-cell-pref-ja",
                  "måske":  "plexus-cell-pref-maybe"}

    with st.container():
      st.markdown('<div class="plexus-cal-boundary"></div>', unsafe_allow_html=True)
      _dag_header()

      for week in calendar.monthcalendar(y, m):
        cols = st.columns(7)
        for i, day in enumerate(week):
            with cols[i]:
                if day == 0:
                    _empty_cell()
                    continue
                d_str   = date(y, m, day).isoformat()
                cfg_typ = date_types.get(d_str)

                if cfg_typ in (OPEN, ACTIVITY):
                    state = st.session_state[sk].get(d_str, "")
                    if state not in PREF_STYLE:
                        state = ""
                    _, _, _, icon, lbl = PREF_STYLE[state]
                    next_s = PREF_CYCLE[state]
                    css_cls = _PREF_CLS.get(state, "plexus-cell-pref-none")
                    st.markdown(
                        f'<div class="plexus-cell-marker {css_cls}"></div>',
                        unsafe_allow_html=True)
                    btn_lbl = f"{DAG_LANG[i][:3]}  {icon} {lbl}\n{day}. {MÅN_GEN[m][:3]}"
                    if st.button(btn_lbl, key=f"vp_{mkey}_{vid}_{d_str}",
                                 use_container_width=True):
                        st.session_state[sk][d_str] = next_s
                        st.rerun()
                elif cfg_typ == CLOSED:
                    _grey_cell_nobutton(DAG_LANG[i][:3], day, MÅN_GEN[m][:3], "📅 Lukket")
                else:
                    _empty_cell()

    return dict(st.session_state[sk])


def render_pref_mobil(mkey: str, vid: str, date_types: dict, existing: dict) -> dict:
    """Mobilvenlig: kun valgbare datoer, 3 kolonner."""
    sk = f"vp_{mkey}_{vid}"
    if sk not in st.session_state:
        st.session_state[sk] = dict(existing)
    rel_dates = sorted(d for d, t in date_types.items() if t in (OPEN, ACTIVITY))
    if not rel_dates:
        st.info("Ingen datoer at vælge endnu.")
        return dict(st.session_state[sk])

    st.markdown(OVERLAY_CAL_CSS, unsafe_allow_html=True)
    for i in range(0, len(rel_dates), 3):
        batch = rel_dates[i:i + 3]
        cols  = st.columns(3)
        for ci, d_str in enumerate(batch):
            try:
                d = date.fromisoformat(d_str)
            except ValueError:
                continue
            state = st.session_state[sk].get(d_str, "")
            if state not in PREF_STYLE:
                state = ""
            bg, border, text, icon, label = PREF_STYLE[state]
            next_s = PREF_CYCLE[state]
            _, _, _, n_icon, n_label = PREF_STYLE[next_s]
            with cols[ci]:
                _colored_cell(bg, border, text, DAG_LANG[d.weekday()][:3],
                               d.day, MÅN_GEN[d.month][:3], f"{icon} {label}", overlay=True)
                if st.button(f"→ {n_icon} {n_label}",
                             key=f"mob_{mkey}_{vid}_{d_str}", use_container_width=True):
                    st.session_state[sk][d_str] = next_s
                    st.rerun()
    return dict(st.session_state[sk])


# ══════════════════════════════════════════════════════════════════════════════
#  FRIVILLIG-SIDE
# ══════════════════════════════════════════════════════════════════════════════
def side_frivillig(data: dict):
    if "vol_id" not in st.session_state:
        st.session_state.vol_id = None
    active_vols = {vid: v for vid, v in data["volunteers"].items()
                   if v.get("active", True)}

    if st.session_state.vol_id is None:
        st.markdown("## 📅 Plexus Vagtplan")
        st.markdown("### 👋 Hvem er du?")
        st.caption("Vælg dit navn for at se din vagtplan eller indsende ønsker.")
        if not active_vols:
            st.info("Ingen frivillige er oprettet endnu. Kontakt administratoren.")
            return
        navne = {v["name"]: vid for vid, v in sorted(active_vols.items(),
                                                       key=lambda x: x[1]["name"])}
        valgt = st.selectbox("", ["— Vælg dit navn —"] + list(navne.keys()),
                             label_visibility="collapsed", key="vol_name_select")
        if valgt != "— Vælg dit navn —":
            st.session_state.vol_id = navne[valgt]
            st.rerun()

        # ── Dagligt roterende meme ───────────────────────────────────────────
        st.markdown("")
        MEMES = [
            ("https://api.memegen.link/images/fine/When_your_shift/starts_in_5_min.png",
             "This is fine 🔥"),
            ("https://api.memegen.link/images/doge/such_volunteer/very_shift.png",
             "Wow 🐕"),
            ("https://api.memegen.link/images/drake/Saying_no_to_the_shift/Showing_up_anyway.png",
             "Drake approves 🙏"),
            ("https://api.memegen.link/images/rollsafe/Cannot_miss_the_deadline/If_I_never_check_my_email.png",
             "Galaxy brain 🧠"),
            ("https://api.memegen.link/images/buzz/Volunteers_everywhere/Volunteers_everywhere.png",
             "Buzz Lightyear ser det 👀"),
            ("https://api.memegen.link/images/db/When_you_sign_up_for_one_shift/And_end_up_doing_three.png",
             "Distracted boyfriend 😅"),
            ("https://api.memegen.link/images/yuno/Why_not_sign_up/For_more_shifts~q.png",
             "Y U NO 😤"),
            ("https://api.memegen.link/images/aag/Shows_up_for_shift/Gets_free_coffee.png",
             "Ancient aliens ☕"),
            ("https://api.memegen.link/images/success/Remembered_to_submit/Shift_preferences.png",
             "Success kid 🤜"),
            ("https://api.memegen.link/images/facepalm/When_you_forget/To_submit_preferences.png",
             "Picard facepalm 🤦"),
            ("https://api.memegen.link/images/woman-cat/Me_yelling_about_my_schedule/The_schedule.png",
             "Woman yelling at cat 😾"),
            ("https://api.memegen.link/images/astronaut/Wait_it_is_my_shift/Always_has_been.png",
             "Always has been 🚀"),
            ("https://api.memegen.link/images/oprah/You_get_a_shift/And_you_get_a_shift.png",
             "Oprah giver vagter 🎁"),
            ("https://api.memegen.link/images/keepcalm/Keep_calm/And_show_up_for_your_shift.png",
             "Keep calm 👑"),
        ]
        day_idx = date.today().timetuple().tm_yday % len(MEMES)
        meme_url, meme_caption = MEMES[day_idx]
        try:
            _, col_m, _ = st.columns([1, 2, 1])
            with col_m:
                st.image(meme_url, caption=meme_caption, use_container_width=True)
        except Exception:
            pass
        # ────────────────────────────────────────────────────────────────────
        return

    vid = st.session_state.vol_id
    if vid not in data["volunteers"]:
        st.session_state.vol_id = None
        st.rerun()
        return

    vol = data["volunteers"][vid]

    st.markdown('<div style="margin-top:20px"></div>', unsafe_allow_html=True)
    col_h, col_b = st.columns([5, 1])
    col_h.markdown(f"## 👋 Hej, {vol['name']}!")
    with col_b:
        st.markdown('<div style="height:28px"></div>', unsafe_allow_html=True)
        if st.button("← Skift", use_container_width=True, key="skift_btn"):
            st.session_state.vol_id = None
            st.rerun()
    st.divider()

    released = {k for k, c in data["monthly_config"].items() if c.get("released")}
    assigned = set(data.get("assignments", {}).keys())
    alle     = sorted(released | assigned, reverse=True)
    if not alle:
        st.info("📭 Ingen måneder er tilgængelige endnu.")
        return

    sel_mk = st.selectbox("📅 Vælg periode", alle, index=0,
                          format_func=mk_label, key="vol_month_select")
    st.markdown("")

    if sel_mk in assigned:
        _vis_vagtplan(data, vid, vol, sel_mk)
    elif sel_mk in released:
        _vis_praeference(data, vid, vol, sel_mk)
    else:
        st.info("Denne måned er ikke frigivet endnu.")


def _vis_vagtplan(data: dict, vid: str, vol: dict, mkey: str):
    asgn = data["assignments"].get(mkey, {})
    if not asgn:
        st.warning("Ingen vagtplan fundet for denne måned.")
        return

    shifts    = asgn.get("shifts", {})
    open_days = asgn.get("open", [])          # alle dage med ≥ min_per frivillige
    activity  = asgn.get("activity", [])      # åbne dage der er aktivitetsdage (subset af open)
    closed_all = asgn.get("closed", [])       # bruges til kalenderfarver

    # Lukkedage til METRIK = konfigurerede planlagte dage der IKKE åbnede.
    # Vi bruger configured_open (gemt af algoritmen) — det er kun de dage
    # admin satte til OPEN eller ACTIVITY i opsætningen. Aldrig hele måneden.
    configured_open = asgn.get("configured_open", None)
    if configured_open is not None:
        lukkede_dage = [d for d in configured_open if d not in set(open_days)]
    else:
        # Bagudkompatibel: lukkede dage der faktisk havde tildelinger
        lukkede_dage = [d for d in closed_all if d in shifts]

    # Mine vagter — frivillig ser kun vagter på åbne dage
    open_set       = set(open_days)
    my_all_shifts  = sorted(d for d, vs in shifts.items() if vid in vs)
    my_open_shifts = [d for d in my_all_shifts if d in open_set]

    kraevet   = vol.get("required_shifts", 2)
    åbne      = len(open_days)
    aktivit   = len(activity)
    lukkede   = len(lukkede_dage)
    total_cfg = åbne + lukkede
    pct       = round(100 * åbne / total_cfg) if total_cfg > 0 else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("✅ Dine vagter",  f"{len(my_open_shifts)}/{kraevet}")
    c2.metric("🟢 Åbningsdage",  åbne)
    c3.metric("📈 Åbningspct.",  f"{pct}%",
              delta=f"{lukkede} lukket" if lukkede else None, delta_color="inverse")

    st.markdown("### 📅 Vagtplan")
    # volunteer_view=True: dage uden nok frivillige viser ikke navne
    st.markdown(
        cal_html_resultater(
            mkey, shifts, open_days, closed_all, activity,
            data["volunteers"], highlight_vid=vid, volunteer_view=True,
            configured_open=asgn.get("configured_open")),
        unsafe_allow_html=True)

    if my_open_shifts:
        st.markdown("---")
        st.markdown("**🗓️ Dine vagter:**")
        for d in my_open_shifts:
            typ = " 🔵" if d in activity else ""
            st.success(f"  ✅ {full_dato(d)}{typ}")
    else:
        st.info("Du er ikke tildelt vagter denne måned.")

    if len(my_open_shifts) < kraevet:
        st.warning(f"⚠️ Du fik {kraevet - len(my_open_shifts)} færre vagt(er) end aftalt.")


def _vis_praeference(data: dict, vid: str, vol: dict, mkey: str):
    cfg      = data["monthly_config"].get(mkey, {})
    if not cfg:
        st.warning("Opsætning mangler for denne måned.")
        return

    try:
        y, m = int(mkey[:4]), int(mkey[5:7])
    except (ValueError, AttributeError):
        st.error("Ugyldig månednøgle.")
        return

    dt       = get_date_types(cfg, y, m)
    min_sel  = cfg.get("min_selections", 5)
    existing = data["preferences"].get(mkey, {}).get(vid, {})
    deadline = cfg.get("deadline", "")

    if data["preferences"].get(mkey, {}).get(vid):
        st.success("✅ Du har allerede gemt dine ønsker — du kan ændre dem nedenfor.")

    st.markdown(f"### ✏️ Vagtønsker – {mk_label(mkey)}")

    if deadline:
        try:
            dl      = date.fromisoformat(deadline)
            dage    = (dl - date.today()).days
            dl_tekst = fmt_dansk_lang(dl)
            dl_kort  = fmt_dansk(dl)
            if dage > 0:
                st.info(f"📅 **Deadline for indsendelse: {dl_tekst}** ({dl_kort}) — {dage} dag(e) tilbage")
            elif dage == 0:
                st.warning(f"⏰ **Deadline er i dag: {dl_tekst}** ({dl_kort}) — send dine ønsker nu!")
            else:
                st.error(f"⌛ Deadline var {dl_tekst} ({dl_kort}) — {-dage} dag(e) siden.")
        except (ValueError, TypeError):
            pass

    st.markdown(
        "Klik på en dato for at skifte:  \n"
        "**✅ Grøn = Ja** &nbsp;|&nbsp; **🟡 Gul = Måske** &nbsp;|&nbsp; **⬜ = Ikke valgt**  \n"
        f"Lukkede dage er grå. Vælg mindst **{min_sel}** datoer. "
        f"Din kvote: **{vol.get('required_shifts', 2)} vagter**.")

    mobile = st.toggle("📱 Mobilvenlig visning (3 kolonner)", key="mob_tog", value=False)
    st.markdown("")

    if mobile:
        prefs = render_pref_mobil(mkey, vid, dt, existing)
    else:
        prefs = render_pref_kalender(mkey, vid, dt, existing)

    markeret = sum(1 for p in prefs.values() if p)
    nok      = markeret >= min_sel
    st.markdown("")
    ci, cb = st.columns([4, 1])
    if markeret == 0:
        ci.markdown("☝️ Klik på en dato ovenfor for at markere.")
    elif nok:
        ci.markdown(f"✅ **{markeret}** datoer valgt — klar til at gemme!")
    else:
        ci.markdown(f"⚠️ **{markeret}** valgt — vælg mindst **{min_sel - markeret}** mere.")

    if cb.button("💾 Gem", type="primary", use_container_width=True,
                 disabled=not nok, key="gem_prefs"):
        if mkey not in data["preferences"]:
            data["preferences"][mkey] = {}
        data["preferences"][mkey][vid] = {k: v for k, v in prefs.items() if v}
        save(data)
        st.success("✅ Dine ønsker er gemt! Du kan ændre dem igen inden vagtplanen genereres.")
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
#  ADMIN-SIDE
# ══════════════════════════════════════════════════════════════════════════════
def side_admin(data: dict):
    st.markdown(
        '<div style="display:none" id="mob-warn"></div>'
        '<style>@media(max-width:720px){'
        '#mob-warn{display:block!important;background:#fff3e0;'
        'border:2px solid #ff9800;border-radius:10px;padding:16px;'
        'text-align:center;font-size:15px;font-weight:600;color:#e65100;'
        'margin-bottom:12px}}'
        '</style>'
        '<div id="mob-warn">⚠️ Admin-panelet er kun tilgængeligt på desktop.</div>',
        unsafe_allow_html=True)

    if "admin_ok" not in st.session_state:
        st.session_state.admin_ok = False
    if not st.session_state.admin_ok:
        st.markdown("## 🔒 Administratorlogin")
        with st.form("login_form"):
            pwd = st.text_input("Adgangskode", type="password",
                                placeholder="Skriv adgangskode og tryk Enter...")
            submitted = st.form_submit_button("🔓 Log ind", type="primary")
        if submitted:
            if pwd == data.get("admin_password", "plexus2024"):
                st.session_state.admin_ok = True
                st.rerun()
            else:
                st.error("❌ Forkert adgangskode.")
        return

    st.markdown('<div style="margin-top:20px"></div>', unsafe_allow_html=True)
    col_h, col_b = st.columns([5, 1])
    col_h.markdown("## ⚙️ Administration")
    with col_b:
        st.markdown('<div style="height:28px"></div>', unsafe_allow_html=True)
        if st.button("🚪 Log ud", use_container_width=True, key="logout_btn"):
            st.session_state.admin_ok = False
            st.rerun()

    t1, t2, t3, t4 = st.tabs(
        ["👥 Frivillige", "📅 Måneds-opsætning", "⚡ Vagttildeling", "📊 Resultater"])
    with t1: _tab_frivillige(data)
    with t2: _tab_opstaetning(data)
    with t3: _tab_tildeling(data)
    with t4: _tab_resultater(data)


# ── Tab: Frivillige ────────────────────────────────────────────────────────────
def _tab_frivillige(data: dict):
    st.markdown("### 👥 Frivillige")
    with st.expander("➕ Tilføj ny frivillig", expanded=not data["volunteers"]):
        with st.form("add_vol", clear_on_submit=True):
            c1, c2, c3 = st.columns([3, 1, 1])
            navn  = c1.text_input("Navn")
            kvote = c2.number_input("Vagter/md.", 1, 20, 2)
            akt   = c3.checkbox("Aktivitetsudvalg")
            if st.form_submit_button("✅ Tilføj"):
                navn = navn.strip()
                if navn:
                    # Tjek for duplikat-navn
                    existing_names = {v["name"].lower() for v in data["volunteers"].values()}
                    if navn.lower() in existing_names:
                        st.warning(f"⚠️ En frivillig med navnet '{navn}' eksisterer allerede.")
                    else:
                        nid = str(data.get("next_id", 1))
                        data["volunteers"][nid] = {
                            "name":             navn,
                            "required_shifts":  int(kvote),
                            "active":           True,
                            "aktivitetsudvalg": bool(akt),
                        }
                        data["next_id"] = int(nid) + 1
                        save(data)
                        st.success(f"✅ {navn} er tilføjet!")
                        st.rerun()
                else:
                    st.warning("Angiv et navn.")

    if not data["volunteers"]:
        st.info("Ingen frivillige oprettet endnu.")
        return

    h1, h2, h3, h4, _ = st.columns([3, 1, 1, 1, 1])
    h1.markdown("**Navn**")
    h2.markdown("**Vagt/mdr**")
    h3.markdown("**Aktiv**")
    h4.markdown("**Akt.udv.**")
    st.markdown("---")

    edits = {}
    for vid, vol in sorted(data["volunteers"].items(), key=lambda x: x[1]["name"]):
        c1, c2, c3, c4, c5 = st.columns([3, 1, 1, 1, 1])
        badge = (f' <span style="background:#dbeafe;color:#1e3a8a;font-size:10px;'
                 f'padding:1px 6px;border-radius:4px">🔵</span>'
                 if vol.get("aktivitetsudvalg") else "")
        c1.markdown(f'**{vol["name"]}**{badge}', unsafe_allow_html=True)
        q  = c2.number_input("", 1, 20, vol.get("required_shifts", 2),
                             key=f"q_{vid}", label_visibility="collapsed")
        a  = c3.checkbox("", vol.get("active", True),
                         key=f"a_{vid}", label_visibility="collapsed")
        ak = c4.checkbox("", vol.get("aktivitetsudvalg", False),
                         key=f"ak_{vid}", label_visibility="collapsed")
        edits[vid] = {"required_shifts": int(q), "active": a, "aktivitetsudvalg": ak}
        if c5.button("🗑️", key=f"del_{vid}", help=f"Slet {vol['name']}"):
            del data["volunteers"][vid]
            save(data)
            st.rerun()

    st.markdown("")
    if st.button("💾 Gem alle ændringer", type="primary",
                 use_container_width=True, key="gem_alle"):
        for vid, vals in edits.items():
            if vid in data["volunteers"]:
                data["volunteers"][vid].update(vals)
        save(data)
        st.success("✅ Alle ændringer gemt!")

    st.markdown("---")
    with st.expander("🔑 Skift admin-adgangskode"):
        with st.form("pwd_form"):
            p1 = st.text_input("Ny adgangskode", type="password")
            p2 = st.text_input("Gentag", type="password")
            if st.form_submit_button("Gem"):
                if p1 and p1 == p2:
                    if len(p1) < 6:
                        st.error("Adgangskoden skal være mindst 6 tegn.")
                    else:
                        data["admin_password"] = p1
                        save(data)
                        st.success("✅ Adgangskode ændret.")
                else:
                    st.error("Adgangskoderne matcher ikke.")


# ── Tab: Måneds-opsætning ──────────────────────────────────────────────────────
def _tab_opstaetning(data: dict):
    st.markdown("### 📅 Måneds-opsætning")

    # Standard: indeværende måned, eller næstkommende ikke-frigivne
    ny, nm = default_setup_month(data)
    c1, c2 = st.columns(2)
    år  = int(c1.number_input("År",  2024, 2030, ny, key="setup_ar"))
    mdr = int(c2.selectbox("Måned", range(1, 13), index=nm - 1,
                            format_func=lambda x: MÅNEDER[x], key="setup_maaned"))

    mkey = mk(år, mdr)
    cfg  = data["monthly_config"].get(mkey, {})
    locked = cfg.get("released", False)
    st.markdown(f"#### {MÅNEDER[mdr]} {år}")
    st.markdown("---")

    if locked:
        st.success(f"✅ **{MÅNEDER[mdr]} {år}** er frigivet og låst.")
        try:
            y_, m_ = int(mkey[:4]), int(mkey[5:7])
            dt = get_date_types(cfg, y_, m_)
        except (ValueError, AttributeError):
            dt = {}

        n_open   = sum(1 for t in dt.values() if t in (OPEN, ACTIVITY))
        n_act    = sum(1 for t in dt.values() if t == ACTIVITY)
        n_closed = sum(1 for t in dt.values() if t == CLOSED)
        c1, c2, c3 = st.columns(3)
        c1.metric("🟢 Åbningsdage", n_open,
                  delta=f"heraf {n_act} aktivitet" if n_act else None, delta_color="off")
        c2.metric("🔴 Lukkede dage", n_closed)
        if cfg.get("deadline"):
            try:
                dl = date.fromisoformat(cfg["deadline"])
                c3.metric("📅 Deadline", fmt_dansk(dl))
            except (ValueError, TypeError):
                pass

        prefs_m = data["preferences"].get(mkey, {})
        aktive  = sum(1 for v in data["volunteers"].values() if v.get("active", True))
        st.info(f"📊 **{len(prefs_m)}/{aktive}** aktive frivillige har indsendt ønsker.")

        if "confirm_revoke" not in st.session_state:
            st.session_state.confirm_revoke = None
        st.markdown('<div class="plexus-danger-btn"></div>', unsafe_allow_html=True)
        if st.button("🔓 Tilbagekald frigivelse", use_container_width=True, key="revoke_btn"):
            st.session_state.confirm_revoke = mkey
        if st.session_state.confirm_revoke == mkey:
            st.error(
                f"⚠️ **Advarsel!** Dette sletter alle indsendte ønsker og eventuelle "
                f"tildelte vagter for **{MÅNEDER[mdr]} {år}**. Er du sikker?")
            ca, cb_ = st.columns(2)
            if ca.button("✅ Ja, tilbagekald", type="primary",
                         use_container_width=True, key="ja_revoke"):
                data["monthly_config"][mkey]["released"] = False
                data["preferences"].pop(mkey, None)
                data["assignments"].pop(mkey, None)
                st.session_state.pop(f"sc_{mkey}", None)
                st.session_state.confirm_revoke = None
                save(data)
                st.success("✅ Frigivelse er tilbagekaldt.")
                st.rerun()
            if cb_.button("❌ Annuller", use_container_width=True, key="nej_revoke"):
                st.session_state.confirm_revoke = None
                st.rerun()
        return

    sk = f"sc_{mkey}"
    if sk not in st.session_state:
        if "date_types" in cfg:
            st.session_state[sk] = dict(cfg["date_types"])
        else:
            st.session_state[sk] = default_date_types(år, mdr)

    st.markdown(
        "**Klik på en dato for at skifte type:**  \n"
        "🟢 **Åben** → 🔴 **Lukket** → 🟢 ...  \n"
        "*(Man/Tirs/Ons/Søn er åbne som standard)*")
    st.markdown("")
    selected = render_setup_kalender(mkey)

    st.markdown("---")
    c3, c4, c5 = st.columns(3)
    min_per = c3.number_input("👤 Min. frivillige/vagt", 1, 10,
                               cfg.get("min_per_shift", 3), key="min_per")
    max_per = c4.number_input("👥 Max. frivillige/vagt", 1, 20,
                               cfg.get("max_per_shift", 3), key="max_per")
    min_sel = c5.number_input("☑️ Min. ønsker/frivillig", 1, 20,
                               cfg.get("min_selections", 5), key="min_sel")

    if int(max_per) < int(min_per):
        st.warning("⚠️ Max. frivillige/vagt må ikke være lavere end min. frivillige/vagt.")

    st.markdown("---")
    st.markdown("**📅 Seneste rettidige indsendelse (deadline)**")
    default_dl = default_deadline(år, mdr)
    # Brug altid default (3 dage før måneden) medmindre en deadline er eksplicit gemt
    # for præcis denne måned. Nøglen inkluderer mkey så widget nulstilles ved månedsskift.
    if cfg.get("deadline"):
        try:
            existing_dl = date.fromisoformat(cfg["deadline"])
        except (ValueError, TypeError):
            existing_dl = default_dl
    else:
        existing_dl = default_dl

    deadline_val = st.date_input(
        "Deadline for indsendelse af ønsker",
        value=existing_dl,
        min_value=date(år - 1, 1, 1),
        max_value=date(år, mdr, 1) - timedelta(days=1),
        key=f"deadline_input_{mkey}",
        format="DD-MM-YYYY",
        help="Vises til de frivillige som en påmindelse. Påvirker ikke systemet automatisk.")
    st.caption(
        f"Standard er 3 dage inden måneden starter "
        f"({fmt_dansk_lang(default_dl)}, dvs. {fmt_dansk(default_dl)})")

    st.markdown("")
    cs, cr = st.columns(2)

    def _build_cfg(released: bool) -> dict:
        return {
            "date_types":     selected,
            "dates":          [d for d, t in selected.items() if t in (OPEN, ACTIVITY)],
            "min_per_shift":  int(min_per),
            "max_per_shift":  int(max_per),
            "min_selections": int(min_sel),
            "deadline":       deadline_val.isoformat(),
            "released":       released,
        }

    if cs.button("💾 Gem (ikke frigivet)", use_container_width=True, key="gem_setup"):
        data["monthly_config"][mkey] = _build_cfg(False)
        save(data)
        st.success(f"✅ Opsætning for {MÅNEDER[mdr]} {år} gemt.")

    if cr.button("🚀 Frigiv til frivillige", type="primary",
                 use_container_width=True, key="frigiv_btn"):
        active_d = [d for d, t in selected.items() if t in (OPEN, ACTIVITY)]
        if not active_d:
            st.error("Vælg mindst én åben eller aktivitetsdag.")
        elif int(max_per) < int(min_per):
            st.error("Max. frivillige/vagt må ikke være lavere end min. frivillige/vagt.")
        else:
            data["monthly_config"][mkey] = _build_cfg(True)
            save(data)
            st.success(f"🎉 **{MÅNEDER[mdr]} {år}** er frigivet!")
            st.rerun()


# ── Tab: Vagttildeling ─────────────────────────────────────────────────────────
def _tab_tildeling(data: dict):
    st.markdown("### ⚡ Vagttildeling")
    frigivne = sorted((k for k, c in data["monthly_config"].items()
                       if c.get("released", False)), reverse=True)
    if not frigivne:
        st.warning("📭 Ingen måneder er frigivet endnu.")
        return

    mkey    = st.selectbox("Vælg måned", frigivne, index=0,
                           format_func=mk_label, key="tildeling_month_select")
    prefs_m = data["preferences"].get(mkey, {})
    aktive  = {vid: v for vid, v in data["volunteers"].items() if v.get("active", True)}
    akt_vols = dict(sorted(
        ((vid, v) for vid, v in aktive.items() if v.get("aktivitetsudvalg")),
        key=lambda x: x[1]["name"]
    ))

    allerede = mkey in data.get("assignments", {})

    # ── Allerede tildelt: simpel visning + Omfordel vagter ────────────────────
    if allerede:
        asgn = data["assignments"][mkey]
        st.caption(f"⏱️ Vagtplan genereret: {asgn.get('generated_at', '–')}  —  Se vagtplanen under fanen 📊 Resultater.")
        st.markdown("---")
        if "confirm_reassign" not in st.session_state:
            st.session_state.confirm_reassign = None
        st.markdown('<div class="plexus-warn-btn"></div>', unsafe_allow_html=True)
        if st.button("⚠️ Omfordel vagter", use_container_width=True, key="reassign_btn"):
            st.session_state.confirm_reassign = mkey
        if st.session_state.confirm_reassign == mkey:
            st.warning(f"⚠️ Dette sletter og genberegner vagtplanen for **{mk_label(mkey)}**. Er du sikker?")
            ca, cb_ = st.columns(2)
            if ca.button("✅ Ja, genberegn", type="primary",
                         use_container_width=True, key="ja_reassign"):
                if not prefs_m:
                    st.error("Ingen ønsker indsendt — kan ikke genberegne.")
                else:
                    # Ryd eksisterende tildeling og låste vagter, beregn forfra
                    del data["assignments"][mkey]
                    st.session_state.pop(f"locked_{mkey}", None)
                    data = auto_assign(data, mkey, locked_shifts=None)
                    save(data)
                    st.session_state.confirm_reassign = None
                    # Nulstil resultater-valg til nyeste måned
                    newest = sorted(data.get("assignments", {}).keys(), reverse=True)
                    if newest:
                        st.session_state["resultater_month_select"] = newest[0]
                    st.success("🎉 Vagtplan genberegnet!")
                    st.balloons()
                    st.rerun()
            if cb_.button("❌ Annuller", use_container_width=True, key="nej_reassign"):
                st.session_state.confirm_reassign = None
                st.rerun()

        st.markdown("---")
        with st.expander("🛡️ Fail-safe: Download rådata"):
            st.caption("Hent alle indsendte ønsker som CSV — uanset om vagter er tildelt.")
            if prefs_m:
                rows = ["Frivillig,Dato,Dag,Ønske"]
                for vid, prefs in prefs_m.items():
                    navn = data["volunteers"].get(vid, {}).get("name", vid)
                    for d_str, val in sorted(prefs.items()):
                        try:
                            dag = DAG_LANG[date.fromisoformat(d_str).weekday()]
                        except (ValueError, KeyError):
                            dag = d_str
                        rows.append(f"{navn},{d_str},{dag},{val}")
                st.download_button(
                    "⬇️ Download ønsker (CSV)",
                    "\n".join(rows).encode("utf-8-sig"),
                    f"plexus_rawdata_{mkey}.csv", "text/csv",
                    use_container_width=True, key="dl_rawdata")
            else:
                st.info("Ingen ønsker indsendt endnu.")
        return

    # ── Ikke tildelt: trin-baseret flow ───────────────────────────────────────
    view_key = f"tildeling_view_{mkey}"
    if view_key not in st.session_state:
        st.session_state[view_key] = "oversigt"
    view = st.session_state[view_key]

    # ─── TRIN 1: Oversigt ────────────────────────────────────────────────────
    if view == "oversigt":
        c1, _ = st.columns(2)
        c1.metric("📋 Indsendte ønsker", f"{len(prefs_m)}/{len(aktive)}")
        col_ja, col_nej = st.columns(2)
        with col_ja:
            st.markdown("**✅ Klar:**")
            for vid, v in aktive.items():
                if vid in prefs_m:
                    s  = sum(1 for p in prefs_m[vid].values() if p == "sikker")
                    ms = sum(1 for p in prefs_m[vid].values() if p == "måske")
                    akt_lbl = " 🔵" if v.get("aktivitetsudvalg") else ""
                    st.write(f"• {v['name']}{akt_lbl}  *(Ja: {s} / Måske: {ms})*")
        with col_nej:
            st.markdown("**❌ Mangler:**")
            for vid, v in aktive.items():
                if vid not in prefs_m:
                    st.write(f"• {v['name']}")
        st.markdown("---")
        if st.button("➡️ Gå videre til vagttildeling", type="primary",
                     use_container_width=True, key="goto_tildeling_btn"):
            st.session_state[view_key] = "tildeling"
            st.rerun()

        st.markdown("---")
        with st.expander("🛡️ Fail-safe: Download rådata"):
            st.caption("Hent alle indsendte ønsker som CSV.")
            if prefs_m:
                rows = ["Frivillig,Dato,Dag,Ønske"]
                for vid, prefs in prefs_m.items():
                    navn = data["volunteers"].get(vid, {}).get("name", vid)
                    for d_str, val in sorted(prefs.items()):
                        try:
                            dag = DAG_LANG[date.fromisoformat(d_str).weekday()]
                        except (ValueError, KeyError):
                            dag = d_str
                        rows.append(f"{navn},{d_str},{dag},{val}")
                st.download_button(
                    "⬇️ Download ønsker (CSV)",
                    "\n".join(rows).encode("utf-8-sig"),
                    f"plexus_rawdata_{mkey}.csv", "text/csv",
                    use_container_width=True, key="dl_rawdata")
            else:
                st.info("Ingen ønsker indsendt endnu.")

    # ─── TRIN 2: Lås og tildel vagter ────────────────────────────────────────
    elif view == "tildeling":
        if st.button("← Tilbage til oversigt", use_container_width=True,
                     key="back_to_oversigt_btn"):
            st.session_state[view_key] = "oversigt"
            st.rerun()

        st.markdown("---")

        # Hent aktive dage fra config
        lock_key = f"locked_{mkey}"
        if lock_key not in st.session_state:
            st.session_state[lock_key] = {}
        locked: dict = st.session_state[lock_key]

        cfg_m    = data["monthly_config"].get(mkey, {})
        y_m, m_m = int(mkey[:4]), int(mkey[5:7])
        dt_m     = get_date_types(cfg_m, y_m, m_m)
        open_days_m = sorted(d for d, t in dt_m.items() if t in (OPEN, ACTIVITY))

        if akt_vols:
            st.markdown("### 🔵 Lås vagter for aktivitetsfrivillige")
            st.caption(
                "Klik på en frivillig under en dato for at låse dem til den vagt. "
                "Låste tildelinger tæller med i kvoten og respekteres af den automatiske fordeling."
            )

            if not open_days_m:
                st.info("Ingen åbningsdage konfigureret for denne måned.")
            else:
                st.markdown(OVERLAY_CAL_CSS, unsafe_allow_html=True)
                with st.container():
                    st.markdown('<div class="plexus-cal-boundary"></div>', unsafe_allow_html=True)
                    _dag_header()
                    for week in calendar.monthcalendar(y_m, m_m):
                        cols = st.columns(7)
                        for i, day in enumerate(week):
                            with cols[i]:
                                if day == 0:
                                    _empty_cell()
                                    continue
                                d_str = date(y_m, m_m, day).isoformat()
                                if d_str not in open_days_m:
                                    _grey_cell_nobutton(DAG_LANG[i], day, MÅN_GEN[m_m][:3], "📅 Lukket")
                                    continue

                                dag_locked = locked.get(d_str, [])
                                navne_html = "".join(
                                    f'<div style="font-size:10px;margin-top:2px;padding:1px 5px;'
                                    f'border-radius:4px;background:#bbdefb;color:#0d47a1;font-weight:600">'
                                    f'🔒 {aktive[vid]["name"]}</div>'
                                    for vid in dag_locked if vid in aktive
                                )
                                oensker_html = ""
                                for vid, v in akt_vols.items():
                                    if vid in dag_locked:
                                        continue
                                    pref = prefs_m.get(vid, {}).get(d_str, "")
                                    if pref == "sikker":
                                        oensker_html += (
                                            f'<div style="font-size:10px;margin-top:2px;padding:1px 5px;'
                                            f'border-radius:4px;background:#c8e6c9;color:#1b5e20">'
                                            f'✅ {v["name"]}</div>')
                                    elif pref == "måske":
                                        oensker_html += (
                                            f'<div style="font-size:10px;margin-top:2px;padding:1px 5px;'
                                            f'border-radius:4px;background:#fff9c4;color:#6d4c00">'
                                            f'🟡 {v["name"]}</div>')
                                bg     = "#e3f2fd" if dag_locked else "#fafafa"
                                border = "#1e88e5" if dag_locked else "#e0e0e0"
                                text_c = "#0d47a1" if dag_locked else "#555"
                                st.markdown(
                                    f'<div class="cal-overlay-cell" style="border:1px solid {border};'
                                    f'border-top:3px solid {border};'
                                    f'padding:8px 5px;background:{bg};'
                                    f'min-height:90px;margin-bottom:2px">'
                                    f'<div style="font-size:10px;font-weight:700;color:{text_c}">{DAG_LANG[i]}</div>'
                                    f'<div style="font-size:22px;font-weight:900;color:{text_c};line-height:1">{day}</div>'
                                    f'<div style="font-size:9px;color:{text_c};margin-bottom:3px">{MÅN_GEN[m_m][:3]}</div>'
                                    f'{navne_html}{oensker_html}</div>',
                                    unsafe_allow_html=True)
                                avail_for_lock = sorted(
                                    [vid for vid in akt_vols if vid not in dag_locked],
                                    key=lambda v: aktive[v]["name"]
                                )
                                if avail_for_lock:
                                    valgt = st.selectbox(
                                        "Tilføj",
                                        ["—"] + [aktive[v]["name"] for v in avail_for_lock],
                                        key=f"lock_sel_{mkey}_{d_str}",
                                        label_visibility="collapsed")
                                    if valgt != "—":
                                        vid_valgt = next(v for v in avail_for_lock
                                                         if aktive[v]["name"] == valgt)
                                        locked.setdefault(d_str, [])
                                        if vid_valgt not in locked[d_str]:
                                            locked[d_str].append(vid_valgt)
                                            st.rerun()
                                if dag_locked:
                                    if st.button("🗑 Ryd", key=f"lock_clear_{mkey}_{d_str}",
                                                 use_container_width=True):
                                        locked.pop(d_str, None)
                                        st.rerun()

        st.markdown("---")
        st.markdown(
            "Klik på **Generer og udgiv vagtplan** for at beregne og udgive "
            "vagtplanen. Vagter låses og frigives til de frivillige.")

        if st.button("🚀 Generer og udgiv vagtplan", type="primary",
                     use_container_width=True, key="tildel_btn"):
            if not prefs_m:
                st.error("Ingen frivillige har indsendt ønsker endnu.")
            else:
                locked_shifts = st.session_state.get(f"locked_{mkey}", {})
                data = auto_assign(data, mkey, locked_shifts=locked_shifts)
                save(data)
                st.session_state[view_key] = "oversigt"
                # Sæt resultater-valg til den nyligt genererede måned
                st.session_state["resultater_month_select"] = mkey
                st.success("🎉 Vagter er tildelt og vagtplanen er udgivet!")
                st.balloons()
                st.rerun()


# ── Tab: Resultater ────────────────────────────────────────────────────────────
def _tab_resultater(data: dict):
    st.markdown("### 📊 Resultater")
    tildelte = sorted(data.get("assignments", {}).keys(), reverse=True)
    if not tildelte:
        st.info("📭 Ingen vagter er tildelt endnu.")
        return

    # Sikr at session-state peger på en gyldig måned
    # (sættes KUN hvis ugyldig – undgår conflict med selectbox-widget)
    if st.session_state.get("resultater_month_select") not in tildelte:
        st.session_state["resultater_month_select"] = tildelte[0]

    # Brug IKKE index= når session-state allerede styrer værdien
    mkey = st.selectbox("Vælg måned", tildelte,
                        format_func=mk_label, key="resultater_month_select")
    asgn = data["assignments"].get(mkey, {})
    if not asgn:
        st.warning("Ingen data for denne måned.")
        return

    vols = data["volunteers"]
    st.caption(f"⏱️ Genereret: {asgn.get('generated_at', '–')}")

    open_days = asgn.get("open", [])
    activity  = asgn.get("activity", [])
    shifts    = asgn.get("shifts", {})

    # Lukkedage og åbnings-% baseres KUN på konfigurerede åbne/aktivitetsdage —
    # ikke hele måneden. Dage der var sat til CLOSED i opsætningen tæller ikke.
    configured_open = asgn.get("configured_open", None)
    if configured_open is not None:
        lukkede_dage = [d for d in configured_open if d not in set(open_days)]
    else:
        lukkede_dage = [d for d in asgn.get("closed", []) if d in shifts]

    åbne      = len(open_days)
    aktivit   = len(activity)
    lukkede   = len(lukkede_dage)
    total_cfg = åbne + lukkede
    pct       = round(100 * åbne / total_cfg) if total_cfg > 0 else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("🟢 Åbningsdage",   åbne)
    c2.metric("🔴 Lukkedage",     lukkede)
    c3.metric("📈 Åbningspct.",   f"{pct}%")

    # Til kalenderen: brug den fulde closed-liste (inkl. setup-lukkede) for farvelægning
    closed_for_cal = asgn.get("closed", [])

    if asgn.get("unmet_quota"):
        with st.expander(f"⚠️ Frivillige med ufyldt kvote ({len(asgn['unmet_quota'])})"):
            for vid, mangler in asgn["unmet_quota"].items():
                navn = vols.get(vid, {}).get("name", vid)
                st.write(f"• **{navn}** — fik {mangler} færre vagt(er) end aftalt")
    else:
        st.success("✅ Alle frivillige har fået deres fulde kvote tildelt")

    st.markdown("### 📅 Kalender-oversigt (Admin — alle tildelinger)")
    # Admin-kalender: volunteer_view=False → navne vises på ALLE dage inkl. lukkedage
    st.markdown(
        cal_html_resultater(mkey, shifts, open_days, closed_for_cal, activity, vols,
                            volunteer_view=False,
                            configured_open=asgn.get("configured_open")),
        unsafe_allow_html=True)

    with st.expander("👤 Oversigt per frivillig"):
        for vid, vol in sorted(vols.items(), key=lambda x: x[1]["name"]):
            if not vol.get("active"):
                continue
            mine    = sorted(d for d, vs in shifts.items() if vid in vs)
            kraevet = vol.get("required_shifts", 2)
            ikon    = "✅" if len(mine) >= kraevet else "⚠️"
            akt     = " 🔵" if vol.get("aktivitetsudvalg") else ""
            st.markdown(f"**{ikon} {vol['name']}{akt}** — {len(mine)}/{kraevet} vagter")
            for d in mine:
                is_open_day = d in open_days
                dag_type = "🔵" if d in activity else ("🟢" if is_open_day else "🔴")
                st.write(f"  • {dag_type} {full_dato(d)}")
            if len(mine) < kraevet:
                st.caption(f"  Fik {kraevet - len(mine)} færre end aftalt.")

    rækker = ["Dato,Dag,Status,Type,Frivillige"]
    for d in sorted(shifts):
        try:
            dag_navn = DAG_LANG[date.fromisoformat(d).weekday()]
        except (ValueError, KeyError):
            dag_navn = d
        navne   = "; ".join(vols[v]["name"] for v in shifts[d] if v in vols)
        is_act  = d in activity
        status  = "Åben" if d in open_days else "Lukket"
        ttype   = "Aktivitet" if is_act else "Normal"
        rækker.append(f"{d},{dag_navn},{status},{ttype},{navne}")

    st.download_button(
        "⬇️ Download vagtplan (CSV)",
        "\n".join(rækker).encode("utf-8-sig"),
        f"plexus_vagtplan_{mkey}.csv", "text/csv",
        use_container_width=True, key="dl_vagtplan")


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    st.set_page_config(
        page_title="Plexus Vagtplan", page_icon="📅", layout="wide",
        initial_sidebar_state="expanded")
    st.markdown(CSS, unsafe_allow_html=True)
    data = load()

    with st.sidebar:
        st.markdown("## 📅 Plexus Vagtplan")
        st.divider()
        side = st.radio("", ["🙋 Frivillig", "⚙️ Administrator"],
                        label_visibility="hidden", key="nav_side")
        st.divider()
        st.caption(f"Version {VERSION}")
        st.caption("Lavet af Fabian Salvatore")

    if side == "🙋 Frivillig":
        side_frivillig(data)
    else:
        side_admin(data)


if __name__ == "__main__":
    main()

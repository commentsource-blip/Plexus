# -*- coding: utf-8 -*-
"""
Plexus Vagtplan
Lavet af Fabian Salvatore
"""
import streamlit as st
import json, os, calendar
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
SETUP_CYCLE = {OPEN:ACTIVITY, ACTIVITY:CLOSED, CLOSED:OPEN}
SETUP_STYLE = {
    OPEN:     ("#c8e6c9","#43a047","#1b5e20","🟢","Åben"),
    CLOSED:   ("#ffcdd2","#e53935","#b71c1c","🔴","Lukket"),
    ACTIVITY: ("#bbdefb","#1e88e5","#0d47a1","🔵","Aktivitet"),
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
    font-size:28px !important;font-weight:800 !important}
div[data-testid="stTabs"] button[data-baseweb="tab"]{
    font-size:14px !important;font-weight:600 !important;padding:8px 18px !important}
.stButton>button{border-radius:10px !important;font-weight:500 !important}
.stButton>button[kind="primary"]{
    background:linear-gradient(135deg,#1565c0,#0d47a1) !important;
    border:none !important;color:white !important}
</style>
"""

# CSS til usynlig overlay-knap der dækker hele datocellen
OVERLAY_CAL_CSS = """
<style>
div[data-testid="stMarkdownContainer"]:has(.cal-overlay-cell)
  + div[data-testid="stButton"] {
    margin-top: -110px !important;
    height: 110px !important;
    position: relative;
    z-index: 10;
}
div[data-testid="stMarkdownContainer"]:has(.cal-overlay-cell)
  + div[data-testid="stButton"] > button {
    height: 110px !important;
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
</style>
"""

# ── Data ──────────────────────────────────────────────────────────────────────
def load() -> dict:
    """Indlæs data fra JSON-fil. Returnerer tomt datasæt ved fejl."""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)
            # Sikr at alle nøglefelter findes
            raw.setdefault("volunteers", {})
            raw.setdefault("monthly_config", {})
            raw.setdefault("preferences", {})
            raw.setdefault("assignments", {})
            raw.setdefault("admin_password", "plexus2024")
            raw.setdefault("next_id", 1)
            return raw
        except (json.JSONDecodeError, OSError):
            st.error("⚠️ Datafilen er beskadiget. Starter med tomt datasæt.")
    return {"volunteers": {}, "monthly_config": {}, "preferences": {},
            "assignments": {}, "admin_password": "plexus2024", "next_id": 1}


def save(data: dict):
    """Gem data til JSON-fil med fejlhåndtering."""
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
def _dag_header(border_color: str, text_color: str):
    cols = st.columns(7)
    for i in range(7):
        is_vd = i in VAGTDAG_IDX
        cols[i].markdown(
            f'<div style="text-align:center;font-size:11px;font-weight:700;'
            f'padding:5px 0;letter-spacing:0.5px;text-transform:uppercase;'
            f'border-bottom:3px solid {"" if not is_vd else border_color};'
            f'color:{text_color if is_vd else "#ccc"}">'
            f'{DAG_LANG[i][:3]}</div>', unsafe_allow_html=True)


def _colored_cell(bg, border, text, dag, day, maan, status, overlay=False):
    cls = ' class="cal-overlay-cell"' if overlay else ''
    st.markdown(
        f'<div{cls} style="background:{bg};border:2px solid {border};'
        f'border-radius:10px;padding:8px 4px 6px;text-align:center;'
        f'min-height:84px">'
        f'<div style="font-size:9px;font-weight:700;color:{text};'
        f'text-transform:uppercase;letter-spacing:0.4px">{dag}</div>'
        f'<div style="font-size:26px;font-weight:900;color:{text};line-height:1.1">{day}</div>'
        f'<div style="font-size:9px;color:{text};opacity:0.8">{maan}</div>'
        f'<div style="font-size:11px;font-weight:600;color:{text};margin-top:3px">{status}</div>'
        f'</div>', unsafe_allow_html=True)


def _grey_cell_nobutton(dag, day, maan, label=""):
    """Grå celle UDEN knap — vises for ikke-valgbare dage."""
    st.markdown(
        f'<div style="background:#f0f0f0;border:1px dashed #ccc;'
        f'border-radius:10px;padding:8px 4px 6px;text-align:center;'
        f'min-height:84px;color:#bbb">'
        f'<div style="font-size:9px;font-weight:700;text-transform:uppercase">{dag}</div>'
        f'<div style="font-size:26px;font-weight:900;line-height:1.1">{day}</div>'
        f'<div style="font-size:9px;opacity:0.8">{maan}</div>'
        f'<div style="font-size:11px;margin-top:3px">{label}</div>'
        f'</div>', unsafe_allow_html=True)


def _non_vagtdag_cell(dag, day, maan):
    """Meget lys celle for dage der ikke er vagtdage (Tor/Fre/Lør)."""
    st.markdown(
        f'<div style="background:#fafafa;border:1px solid #f0f0f0;'
        f'border-radius:10px;padding:8px 4px 6px;text-align:center;'
        f'min-height:84px;color:#ddd">'
        f'<div style="font-size:9px;font-weight:700;text-transform:uppercase;'
        f'letter-spacing:0.4px">{dag}</div>'
        f'<div style="font-size:26px;font-weight:900;line-height:1.1">{day}</div>'
        f'<div style="font-size:9px;opacity:0.8">{maan}</div>'
        f'</div>', unsafe_allow_html=True)


def _empty_cell():
    st.markdown('<div style="min-height:110px"></div>', unsafe_allow_html=True)


# ── Fordelingsalgoritme ───────────────────────────────────────────────────────
def auto_assign(data: dict, mkey: str) -> dict:
    """
    TRE-FASE VAGTTILDELING
    ══════════════════════

    Prioriteter (højest → lavest):
      1. Flest mulige åbne dage  (≥ min_per frivillige tildelt)
      2. Aktivitetsdage: aktivitetsudvalg-frivillige tildeles FØR andre
      3. Ja-præferencer (sikker) > Måske-præferencer > Ingen præference
      4. Ligelig fordeling af vagter (ingen bør have 0 mens andre har mange)
      5. Respektér min_per og max_per per vagt

    Fase 1 – Åbningsoptimering (kun præference-frivillige):
      Behandl dage iterativt, hårdest først (færrest villige = hårdest).
      Gentag gennemgang indtil ingen fremskridt — sikrer at ændringer i
      kvoter fra én dag kan "låse op" for andre dage i næste iteration.

    Fase 2 – Kvotefordeling + hjælp til åbning:
      Frivillige med resterende kvote tildeles dag-for-dag.
      En frivillig der KAN åbne en dag (mangler præcis den ene) prioriteres.
      Vagter på dage der ender som lukkede tæller IKKE mod kvoten
      (unmet_quota beregnes kun ud fra åbne dage).

    Fase 3 – Nødpass uden præferencekrav:
      Resterende lukkede dage forsøges åbnet med frivillige uden præference,
      prioriteret fra tættest-på-åbning og ned.
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
    is_akt   = {vid: bool(vols[vid].get("aktivitetsudvalg", False)) for vid in active}

    # Edge-case: ingen aktive dage eller frivillige
    if not active_d or not active:
        data["assignments"][mkey] = {
            "shifts": {}, "open": [],
            "closed": sorted(dt.keys()),
            "activity": [], "unmet_quota": {},
            "generated_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
        }
        return data

    # Præference-matrix: 2 = sikker/ja, 1 = måske, 0 = ingen præference
    prio: dict[str, dict[str, int]] = {
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
    shifts: dict[str, list[str]] = {d: [] for d in active_d}

    # ── Hjælpefunktioner ────────────────────────────────────────────────────

    def is_act_day(d: str) -> bool:
        return dt.get(d) == ACTIVITY

    def eligible(vid: str, d: str, allow_no_pref: bool = False) -> bool:
        """Kan vid tildeles dag d?"""
        return (
            vid not in shifts[d]
            and remaining[vid] > 0
            and len(shifts[d]) < max_per
            and (allow_no_pref or prio[vid][d] > 0)
        )

    def candidate_score(vid: str, d: str) -> tuple:
        """
        Prioritetsnøgle — lav værdi = høj prioritet.

        Niveau 1 — Aktivitetsdag + aktivitetsudvalg  (0 = ja, 1 = nej)
        Niveau 2 — Præference  (0 = ja, 1 = måske, 2 = ingen)
        Niveau 3 — Flest resterende vagter foretrækkes (lighed)
        """
        akt  = 0 if (is_act_day(d) and is_akt[vid]) else 1
        pref = 2 - prio[vid][d]          # 0=ja, 1=måske, 2=ingen
        rem  = -remaining[vid]            # negativ → størst remaining = bedst
        return (akt, pref, rem)

    def fill_day(d: str, allow_no_pref: bool = False) -> bool:
        """
        Forsøg at åbne dag d op til min_per.

        Kritisk: tildeler KUN hvis vi faktisk KAN nå min_per med de
        tilgængelige kandidater — ellers spildes ingen kvoter.
        Returnerer True hvis dagen er åben (≥ min_per) bagefter.
        """
        if len(shifts[d]) >= min_per:
            return True
        cands = sorted(
            [v for v in active if eligible(v, d, allow_no_pref)],
            key=lambda v: candidate_score(v, d),
        )
        needed = min_per - len(shifts[d])
        if len(cands) < needed:
            return False    # Ikke nok kandidater — gør INGENTING, bevar kvoter
        for v in cands:
            if len(shifts[d]) >= min_per:
                break
            shifts[d].append(v)
            remaining[v] -= 1
        return len(shifts[d]) >= min_per

    # ════════════════════════════════════════════════════════════════════════
    # FASE 1 — Åbningsoptimering med præferencer
    # ════════════════════════════════════════════════════════════════════════
    #
    # Aktivitetsdage behandles ALTID FØR normale åbningsdage — det er den
    # højeste prioritet i hele algoritmen.
    #
    # Inden for hver dagtype (aktivitet / normal) sorteres dage efter
    # sværhedsgrad: færrest tilgængelige præference-kandidater = hårdest = FØRST.
    # Kun dage der faktisk KAN åbnes (nok kandidater) medtages.
    #
    # Iteration gentages så længe mindst én ny dag åbner pr. gennemgang:
    # åbning af dag A bruger kvoter og kan umuliggøre åbning af dag B,
    # så vi genberegner prioritet efter hver runde.

    prev_open = -1
    while True:
        open_now = sum(1 for d in active_d if len(shifts[d]) >= min_per)
        if open_now == prev_open:
            break           # ingen fremskridt → stop
        prev_open = open_now

        def _n_eligible(d: str) -> int:
            return sum(1 for v in active if eligible(v, d, False))

        can_open = sorted(
            [d for d in active_d
             if len(shifts[d]) < min_per
             and _n_eligible(d) >= (min_per - len(shifts[d]))],
            key=lambda d: (
                0 if is_act_day(d) else 1,  # aktivitetsdage FØRST
                _n_eligible(d),             # dernæst: hårdest (færrest kandidater)
            ),
        )
        for d in can_open:
            fill_day(d, allow_no_pref=False)

    # ════════════════════════════════════════════════════════════════════════
    # FASE 2 — Kvotefordeling + hjælp til åbning
    # ════════════════════════════════════════════════════════════════════════
    #
    # Én frivillig tildeles ad gangen — den med FLEST resterende vagter
    # for at sikre ligelig fordeling.
    #
    # Prioritetsrækkefølge for dagvalg (lav score = høj prioritet):
    #
    #   Niveau A — dagtype × akt.udvalg-match:
    #     0 = aktivitetsdag OG frivillig er aktivitetsudvalg
    #     1 = aktivitetsdag (frivillig er ikke aktivitetsudvalg)
    #     2 = normal åbningsdag
    #
    #   Niveau B — åbningsstatus (opn):
    #     0 = dag åbner med præcis denne frivillig (gap == 1)
    #     1 = dag er allerede åben
    #     2 = dag mangler 2 (hjælp stadig nyttig)
    #     3 = dag mangler 3+ (langt fra åbning)
    #
    #   Niveau C — præference: 0=ja, 1=måske, 2=ingen
    #   Niveau D — færreste allerede tildelt (fordel lighedsprincippet)
    #
    # Dage der aldrig kan åbnes springes over (ingen tilgængelige kandidater).

    total_remaining = sum(remaining.values())
    for _ in range(total_remaining * 2 + 1):
        vols_left = [v for v in active if remaining[v] > 0]
        if not vols_left:
            break
        vols_left.sort(key=lambda v: -remaining[v])   # flest resterende FØRST

        assigned = False
        for vid in vols_left:
            best_d:     str | None   = None
            best_score: tuple | None = None

            for d in active_d:
                if not eligible(vid, d, allow_no_pref=True):
                    continue

                gap     = min_per - len(shifts[d])   # ≤ 0 = allerede åben
                is_open = gap <= 0

                # Spring over dage der aldrig kan åbnes
                if not is_open:
                    avail = sum(1 for v in active if eligible(v, d, True))
                    if avail < gap:
                        continue

                # Niveau A: dagtype × akt.udvalg
                if is_act_day(d):
                    dtype = 0 if is_akt[vid] else 1
                else:
                    dtype = 2

                # Niveau B: åbningsstatus
                opn = (0 if gap == 1
                       else 1 if is_open
                       else 2 if gap == 2
                       else 3)

                pref  = 2 - prio[vid][d]    # 0=ja, 1=måske, 2=ingen
                fill  = len(shifts[d])

                score = (dtype, opn, pref, fill)
                if best_score is None or score < best_score:
                    best_score = score
                    best_d = d

            if best_d is not None:
                shifts[best_d].append(vid)
                remaining[vid] -= 1
                assigned = True
                break   # Omstart med opdateret remaining-sortering

        if not assigned:
            break

    # ════════════════════════════════════════════════════════════════════════
    # FASE 3 — Nødpass: åbn resterende dage uden præferencekrav
    # ════════════════════════════════════════════════════════════════════════
    #
    # Aktivitetsdage behandles stadig FØRST, dernæst normale dage.
    # Inden for hver type: tættest-på-åbning (flest allerede tildelt) FØRST.
    # fill_day afviser dage der ikke kan nå min_per — ingen spild.

    still_closed = sorted(
        [d for d in active_d if len(shifts[d]) < min_per],
        key=lambda d: (
            0 if is_act_day(d) else 1,  # aktivitetsdage FØRST
            -len(shifts[d]),            # tættest på åbning
        ),
    )
    for d in still_closed:
        fill_day(d, allow_no_pref=True)

    # ════════════════════════════════════════════════════════════════════════
    # KLASSIFICÉR DAGE OG GEM
    # ════════════════════════════════════════════════════════════════════════

    open_set   = {d for d in active_d if len(shifts[d]) >= min_per}
    open_d     = sorted(open_set)
    closed_d   = sorted(
        ({d for d in active_d if d not in open_set})
        | ({d for d, t in dt.items() if t == CLOSED})
    )
    activity_d = sorted(d for d in open_set if is_act_day(d))

    # Uopfyldt kvote beregnes KUN ud fra åbne dage.
    # Vagter på lukkede dage (for få frivillige) tæller ikke.
    open_shifts = {
        vid: sum(1 for d in open_set if vid in shifts[d])
        for vid in active
    }
    unmet = {
        vid: quota[vid] - open_shifts[vid]
        for vid in active
        if open_shifts[vid] < quota[vid]
    }

    data["assignments"][mkey] = {
        "shifts":              {d: lst for d, lst in shifts.items()},
        "open":                open_d,
        "closed":              closed_d,
        "activity":            activity_d,
        # Alle dage der var konfigureret som OPEN eller ACTIVITY i opsætningen.
        # Bruges til korrekt beregning af lukkedage og åbningsprocent:
        # vi tæller KUN dage der faktisk var planlagt åbne — ikke hele måneden.
        "configured_open":     active_d,
        "unmet_quota":         unmet,
        "generated_at":        datetime.now().strftime("%d/%m/%Y %H:%M"),
    }
    return data


# ══════════════════════════════════════════════════════════════════════════════
#  STATISK HTML-KALENDER
# ══════════════════════════════════════════════════════════════════════════════
def _html_thead() -> str:
    cells = "".join(
        f'<th style="padding:10px 4px;font-size:12px;font-weight:700;'
        f'letter-spacing:0.5px;border:1px solid #e0e0e0;'
        f'background:{"#f0f7ff" if i in VAGTDAG_IDX else "#f9f9f9"};'
        f'color:{"#1565c0" if i in VAGTDAG_IDX else "#bbb"};'
        f'border-bottom:3px solid {"#1565c0" if i in VAGTDAG_IDX else "#e0e0e0"}">'
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
                rows += ('<td style="background:#fafafa;border:1px solid #ececec;'
                         'padding:6px;min-width:100px"></td>')
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
                         f'padding:8px 5px;vertical-align:top;min-width:100px">'
                         f'<div style="font-size:10px;font-weight:700;color:{hdr}">{DAG_LANG[i]}</div>'
                         f'<div style="font-size:22px;font-weight:900;color:{hdr};line-height:1">{day}</div>'
                         f'<div style="font-size:9px;color:{hdr};margin-bottom:2px">{MÅN_GEN[m]}</div>'
                         f'<div style="font-size:10px;color:{hdr}">{dot} {status_txt}</div>'
                         f'{names_html}</td>')

            elif was_planned_open:
                # ── For få frivillige (planlagt åben, men lukket) ────
                bg, hdr = "#ffebee", "#c62828"
                navne = [(v, vols[v]["name"]) for v in shifts.get(d_str, []) if v in vols]

                if volunteer_view:
                    # Frivillige ser ikke hvem der er tildelt på lukkede dage
                    body_html = ('<div style="font-size:10px;color:#c62828;'
                                 'margin-top:4px;font-style:italic">Lukket</div>')
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
                         f'padding:8px 5px;vertical-align:top;min-width:100px">'
                         f'<div style="font-size:10px;font-weight:700;color:{hdr}">{DAG_LANG[i]}</div>'
                         f'<div style="font-size:22px;font-weight:900;color:{hdr};line-height:1">{day}</div>'
                         f'<div style="font-size:9px;color:{hdr};margin-bottom:2px">{MÅN_GEN[m]}</div>'
                         f'<div style="font-size:10px;color:{hdr}">🔴</div>'
                         f'{body_html}</td>')

            else:
                # ── Planlagt lukket (sat til CLOSED i opsætningen) ───
                rows += (f'<td style="background:#f5f5f5;border:1px solid #e0e0e0;'
                         f'padding:8px 5px;vertical-align:top;min-width:100px;opacity:0.6">'
                         f'<div style="font-size:10px;font-weight:700;color:#9e9e9e">{DAG_LANG[i]}</div>'
                         f'<div style="font-size:22px;font-weight:900;color:#bdbdbd;line-height:1">{day}</div>'
                         f'<div style="font-size:9px;color:#bdbdbd;margin-bottom:2px">{MÅN_GEN[m]}</div>'
                         f'<div style="font-size:10px;color:#bdbdbd">📅 Planlagt lukket</div>'
                         f'</td>')

        rows += "</tr>"

    return (f'<div style="overflow-x:auto;border-radius:12px;border:1px solid #e0e0e0;overflow:hidden">'
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

    st.markdown(OVERLAY_CAL_CSS, unsafe_allow_html=True)
    _dag_header("#2e7d32", "#2e7d32")
    for week in calendar.monthcalendar(y, m):
        cols = st.columns(7)
        for i, day in enumerate(week):
            with cols[i]:
                if day == 0:
                    _empty_cell()
                    continue
                d_str = date(y, m, day).isoformat()
                state = st.session_state[sk].get(d_str, CLOSED)
                if state not in SETUP_STYLE:
                    state = CLOSED
                bg, border, text, icon, label = SETUP_STYLE[state]
                next_s = SETUP_CYCLE[state]
                _colored_cell(bg, border, text, DAG_LANG[i][:3], day, MÅN_GEN[m][:3],
                               f"{icon} {label}", overlay=True)
                if st.button(f"→ {SETUP_STYLE[next_s][3]} {SETUP_STYLE[next_s][4]}",
                             key=f"sc_{mkey}_{d_str}", use_container_width=True):
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

    st.markdown(OVERLAY_CAL_CSS, unsafe_allow_html=True)
    # Dag-header: vis alle 7 dage neutralt — enhver dag kan være åben i opsætningen
    cols_h = st.columns(7)
    for i in range(7):
        cols_h[i].markdown(
            f'<div style="text-align:center;font-size:11px;font-weight:700;'
            f'padding:5px 0;letter-spacing:0.5px;text-transform:uppercase;'
            f'border-bottom:3px solid #1565c0;color:#1565c0">'
            f'{DAG_LANG[i][:3]}</div>', unsafe_allow_html=True)

    for week in calendar.monthcalendar(y, m):
        cols = st.columns(7)
        for i, day in enumerate(week):
            with cols[i]:
                if day == 0:
                    _empty_cell()
                    continue
                d_str   = date(y, m, day).isoformat()
                cfg_typ = date_types.get(d_str)   # OPEN, CLOSED, ACTIVITY eller None

                if cfg_typ in (OPEN, ACTIVITY):
                    # Valgbar dag — klik overalt på cellen
                    state = st.session_state[sk].get(d_str, "")
                    if state not in PREF_STYLE:
                        state = ""
                    bg, border, text, icon, label = PREF_STYLE[state]
                    next_s = PREF_CYCLE[state]
                    _, _, _, n_icon, n_label = PREF_STYLE[next_s]
                    _colored_cell(bg, border, text, DAG_LANG[i][:3], day, MÅN_GEN[m][:3],
                                   f"{icon} {label}", overlay=True)
                    if st.button(f"→ {n_icon} {n_label}",
                                 key=f"vp_{mkey}_{vid}_{d_str}", use_container_width=True):
                        st.session_state[sk][d_str] = next_s
                        st.rerun()
                elif cfg_typ == CLOSED:
                    # Planlagt lukket dag — grå, ingen knap
                    _grey_cell_nobutton(DAG_LANG[i][:3], day, MÅN_GEN[m][:3], "📅 Planlagt lukket")
                else:
                    # Dag uden konfiguration (burde ikke ske) — neutral tom celle
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
        return

    vid = st.session_state.vol_id
    if vid not in data["volunteers"]:
        st.session_state.vol_id = None
        st.rerun()
        return

    vol = data["volunteers"][vid]

    st.markdown('<div style="margin-top:30px"></div>', unsafe_allow_html=True)
    col_h, col_b = st.columns([5, 1])
    col_h.markdown(f"## 👋 Hej, {vol['name']}!")
    if col_b.button("← Skift", use_container_width=True, key="skift_btn"):
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
    c2.metric("🟢 Åbningsdage",  åbne,
              delta=f"heraf {aktivit} aktivitet" if aktivit else None, delta_color="off")
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
        pwd = st.text_input("Adgangskode", type="password",
                            placeholder="Skriv adgangskode...")
        if st.button("🔓 Log ind", type="primary", key="login_btn"):
            if pwd == data.get("admin_password", "plexus2024"):
                st.session_state.admin_ok = True
                st.rerun()
            else:
                st.error("❌ Forkert adgangskode.")
        return

    st.markdown('<div style="margin-top:20px"></div>', unsafe_allow_html=True)
    col_h, col_b = st.columns([5, 1])
    col_h.markdown("## ⚙️ Administration")
    if col_b.button("🚪 Log ud", use_container_width=True, key="logout_btn"):
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
    h2.markdown("**Vgt/md.**")
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
        "🟢 **Åben** → 🔵 **Aktivitet** → 🔴 **Lukket** → 🟢 ...  \n"
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
    default_dl  = default_deadline(år, mdr)
    existing_dl = default_dl
    if cfg.get("deadline"):
        try:
            existing_dl = date.fromisoformat(cfg["deadline"])
        except (ValueError, TypeError):
            existing_dl = default_dl

    deadline_val = st.date_input(
        "Deadline for indsendelse af ønsker",
        value=existing_dl,
        min_value=date(år - 1, 1, 1),
        max_value=date(år, mdr, 1) - timedelta(days=1),
        key="deadline_input",
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
    st.markdown("### ⚡ Automatisk vagttildeling")
    frigivne = sorted(k for k, c in data["monthly_config"].items()
                      if c.get("released", False))
    if not frigivne:
        st.warning("📭 Ingen måneder er frigivet endnu.")
        return

    # Standard: den NYESTE frigivne måned
    default_idx = len(frigivne) - 1

    mkey    = st.selectbox("Vælg måned", frigivne, index=default_idx,
                           format_func=mk_label, key="tildeling_month_select")
    prefs_m = data["preferences"].get(mkey, {})
    aktive  = {vid: v for vid, v in data["volunteers"].items() if v.get("active", True)}

    c1, c2 = st.columns(2)
    c1.metric("📋 Indsendte ønsker", f"{len(prefs_m)}/{len(aktive)}")

    col_ja, col_nej = st.columns(2)
    with col_ja:
        st.markdown("**✅ Klar:**")
        for vid, v in aktive.items():
            if vid in prefs_m:
                s  = sum(1 for p in prefs_m[vid].values() if p == "sikker")
                ms = sum(1 for p in prefs_m[vid].values() if p == "måske")
                akt = " 🔵" if v.get("aktivitetsudvalg") else ""
                st.write(f"• {v['name']}{akt}  *(Ja: {s} / Måske: {ms})*")
    with col_nej:
        st.markdown("**❌ Mangler:**")
        for vid, v in aktive.items():
            if vid not in prefs_m:
                st.write(f"• {v['name']}")

    st.markdown("---")
    allerede = mkey in data.get("assignments", {})

    if allerede:
        st.info("ℹ️ Vagter er allerede tildelt for denne måned.")
        if "confirm_reassign" not in st.session_state:
            st.session_state.confirm_reassign = None
        if st.button("🔄 Omfordel vagter", use_container_width=True, key="reassign_btn"):
            st.session_state.confirm_reassign = mkey
        if st.session_state.confirm_reassign == mkey:
            st.warning(f"⚠️ Dette overskriver vagtplanen for **{mk_label(mkey)}**. Er du sikker?")
            ca, cb_ = st.columns(2)
            if ca.button("✅ Ja, omfordel", type="primary",
                         use_container_width=True, key="ja_reassign"):
                if not prefs_m:
                    st.error("Ingen ønsker indsendt.")
                else:
                    data = auto_assign(data, mkey)
                    save(data)
                    st.session_state.confirm_reassign = None
                    st.success("🎉 Vagter omfordelt!")
                    st.balloons()
                    st.rerun()
            if cb_.button("❌ Annuller", use_container_width=True, key="nej_reassign"):
                st.session_state.confirm_reassign = None
                st.rerun()
    else:
        if st.button("🚀 Tildel vagter automatisk", type="primary",
                     use_container_width=True, key="tildel_btn"):
            if not prefs_m:
                st.error("Ingen frivillige har indsendt ønsker endnu.")
            else:
                data = auto_assign(data, mkey)
                save(data)
                st.success("🎉 Vagter er tildelt!")
                st.balloons()
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


# ── Tab: Resultater ────────────────────────────────────────────────────────────
def _tab_resultater(data: dict):
    st.markdown("### 📊 Resultater")
    tildelte = sorted(data.get("assignments", {}).keys(), reverse=True)
    if not tildelte:
        st.info("📭 Ingen vagter er tildelt endnu.")
        return

    # Standard: den seneste måned med tildelte vagter (index=0 da reverse=True)
    mkey = st.selectbox("Vælg måned", tildelte, index=0,
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
    c1.metric("🟢 Åbningsdage",   åbne,
              delta=f"heraf {aktivit} aktivitet" if aktivit else None, delta_color="off")
    c2.metric("🔴 Lukkedage",     lukkede,
              delta="af planlagte dage", delta_color="off")
    c3.metric("📈 Åbningspct.",   f"{pct}%")

    # Til kalenderen: brug den fulde closed-liste (inkl. setup-lukkede) for farvelægning
    closed_for_cal = asgn.get("closed", [])

    if asgn.get("unmet_quota"):
        with st.expander("⚠️ Frivillige med ufyldt kvote"):
            for vid, mangler in asgn["unmet_quota"].items():
                navn = vols.get(vid, {}).get("name", vid)
                st.write(f"• **{navn}** mangler {mangler} vagt(er)")

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

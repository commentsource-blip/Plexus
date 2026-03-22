# -*- coding: utf-8 -*-
"""
Plexus Vagtplan
Lavet af Fabian Salvatore
"""
import streamlit as st
import json, os, calendar
from datetime import date, datetime

# ── Konstanter ────────────────────────────────────────────────────────────────
VERSION     = date.today().strftime("%d.%m.%Y")
DATA_FILE   = "plexus_data.json"
VAGTDAG_IDX = {0, 1, 2, 6}       # Man=0, Tirs=1, Ons=2, Søn=6
DAG_KORT    = {0:"Man", 1:"Tirs", 2:"Ons", 3:"Tor", 4:"Fre", 5:"Lør", 6:"Søn"}
DAG_LANG    = {0:"Mandag", 1:"Tirsdag", 2:"Onsdag", 6:"Søndag"}
MÅNEDER     = ["","Januar","Februar","Marts","April","Maj","Juni",
               "Juli","August","September","Oktober","November","December"]

# ── Globalt CSS ───────────────────────────────────────────────────────────────
CSS = """
<style>
.block-container { padding-top: 1.5rem !important; }
div[data-testid="stMetric"] {
    background: linear-gradient(135deg,#f0f7ff,#e8f5e9);
    border-radius:10px; padding:14px 18px;
    border: 1px solid #e0e0e0;
}
div[data-testid="stMetric"] label { font-size:13px !important; color:#555 !important; }
div[data-testid="stMetric"] [data-testid="stMetricValue"] { font-size:26px !important; font-weight:700 !important; }
div[data-testid="stTabs"] button[data-baseweb="tab"] {
    font-size:15px; font-weight:600; padding: 8px 20px;
}
.stButton > button {
    border-radius: 8px !important;
    font-weight: 500 !important;
}
</style>
"""

# ── Data-hjælpere ─────────────────────────────────────────────────────────────
def load() -> dict:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "volunteers": {},
        "monthly_config": {},
        "preferences": {},
        "assignments": {},
        "admin_password": "plexus2024",
        "next_id": 1,
    }

def save(data: dict):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def mk(y: int, m: int) -> str:
    return f"{y}-{m:02d}"

def mk_label(k: str) -> str:
    y, m = k.split("-")
    return f"{MÅNEDER[int(m)]} {y}"

def all_vagtdates(y: int, m: int) -> list:
    n = calendar.monthrange(y, m)[1]
    return [date(y, m, d).isoformat()
            for d in range(1, n + 1)
            if date(y, m, d).weekday() in VAGTDAG_IDX]

def fmt(d_str: str) -> str:
    d = date.fromisoformat(d_str)
    return f"{DAG_LANG.get(d.weekday(), DAG_KORT[d.weekday()])} {d.day}/{d.month}"

def next_plan_month(data: dict) -> tuple:
    """Måned der skal planlægges = måneden efter den seneste tildelte."""
    assigned = sorted(data.get("assignments", {}).keys())
    if assigned:
        y, m = int(assigned[-1][:4]), int(assigned[-1][5:7])
    else:
        now = datetime.now()
        y, m = now.year, now.month
    return (y + 1, 1) if m == 12 else (y, m + 1)

# ── Fordelingsalgoritme ───────────────────────────────────────────────────────
def auto_assign(data: dict, mkey: str) -> dict:
    cfg      = data["monthly_config"].get(mkey, {})
    dates    = cfg.get("dates", [])
    min_per  = cfg.get("min_per_shift", 3)
    max_per  = cfg.get("max_per_shift", 6)
    prefs_m  = data["preferences"].get(mkey, {})
    vols     = data["volunteers"]
    active   = [vid for vid, v in vols.items() if v.get("active", True)]

    prio = {
        vid: {
            d: (2 if prefs_m.get(vid, {}).get(d) == "sikker"
                else 1 if prefs_m.get(vid, {}).get(d) == "måske"
                else 0)
            for d in dates
        }
        for vid in active
    }
    remaining = {vid: vols[vid].get("required_shifts", 2) for vid in active}
    shifts    = {d: [] for d in dates}

    sorted_dates = sorted(dates, key=lambda d: sum(1 for v in active if prio[v][d] > 0))

    # Fase 1: fyld min_per med "Ja" (prio=2) først, derefter "Måske" (prio=1)
    for phase_prio in [2, 1]:
        for d in sorted_dates:
            if len(shifts[d]) >= min_per:
                continue
            cands = [v for v in active
                     if prio[v][d] >= phase_prio
                     and remaining[v] > 0
                     and v not in shifts[d]
                     and len(shifts[d]) < max_per]
            cands.sort(key=lambda v: (prio[v][d], remaining[v]), reverse=True)
            for v in cands:
                if len(shifts[d]) >= min_per:
                    break
                shifts[d].append(v)
                remaining[v] -= 1

    # Fase 2: fyld resterende kvote
    for vid in sorted(active, key=lambda v: remaining[v], reverse=True):
        while remaining[vid] > 0:
            cands = [d for d in dates
                     if prio[vid][d] > 0
                     and vid not in shifts[d]
                     and len(shifts[d]) < max_per]
            if not cands:
                break
            cands.sort(key=lambda d: (len(shifts[d]) >= min_per, -prio[vid][d], len(shifts[d])))
            shifts[cands[0]].append(vid)
            remaining[vid] -= 1

    open_d   = [d for d in dates if len(shifts[d]) >= min_per]
    closed_d = [d for d in dates if len(shifts[d]) <  min_per]

    data["assignments"][mkey] = {
        "shifts": shifts,
        "open": open_d,
        "closed": closed_d,
        "unmet_quota": {v: remaining[v] for v in active if remaining[v] > 0},
        "generated_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
    }
    return data

# ══════════════════════════════════════════════════════════════════════════════
#  KALENDER-HTML (statisk visning)
# ══════════════════════════════════════════════════════════════════════════════
def _dag_header_html(vagt_color: str, vagt_border: str) -> str:
    cells = ""
    for i in range(7):
        name  = DAG_KORT[i]
        is_vd = i in VAGTDAG_IDX
        cells += (
            f'<th style="padding:10px 4px;font-size:13px;font-weight:700;'
            f'border:1px solid #e0e0e0;letter-spacing:0.5px;'
            f'background:{"#f0f7ff" if is_vd else "#f9f9f9"};'
            f'color:{vagt_color if is_vd else "#bbb"};'
            f'border-bottom:3px solid {vagt_border if is_vd else "#e0e0e0"}">'
            f'{name}</th>'
        )
    return f"<thead><tr>{cells}</tr></thead>"


def cal_html_resultater(mkey: str, shifts: dict, open_days: list, vols: dict) -> str:
    """Kalender til administrator-resultater: åben=grøn, lukket=rød, frivillige vist."""
    y, m   = int(mkey[:4]), int(mkey[5:7])
    weeks  = calendar.monthcalendar(y, m)
    rows   = ""
    for week in weeks:
        rows += "<tr>"
        for i, day in enumerate(week):
            if day == 0:
                rows += '<td style="background:#fafafa;border:1px solid #ececec;padding:6px"></td>'
                continue
            d_str   = date(y, m, day).isoformat()
            is_vdag = i in VAGTDAG_IDX
            is_open = d_str in open_days
            navne   = [vols[v]["name"] for v in shifts.get(d_str, []) if v in vols]
            if is_vdag:
                if is_open:
                    bg, hdr_color, dot = "#e8f5e9", "#1b5e20", "🟢"
                else:
                    bg, hdr_color, dot = "#ffebee", "#b71c1c", "🔴"
                names_html = "".join(
                    f'<div style="font-size:11px;margin-top:2px;background:#ffffffcc;'
                    f'border-radius:4px;padding:1px 5px;color:#333">{n}</div>'
                    for n in navne
                )
                rows += (
                    f'<td style="background:{bg};border:1px solid #ccc;'
                    f'padding:8px 5px;vertical-align:top;min-width:82px">'
                    f'<div style="font-size:17px;font-weight:800;color:{hdr_color}">{day}</div>'
                    f'<div style="font-size:10px;color:{hdr_color};margin-bottom:2px">{dot} {"Åben" if is_open else "Lukket"}</div>'
                    f'{names_html}</td>'
                )
            else:
                rows += (
                    f'<td style="background:#fafafa;border:1px solid #ececec;'
                    f'padding:8px 4px;text-align:center;color:#ccc;vertical-align:top">'
                    f'<div style="font-size:14px">{day}</div></td>'
                )
        rows += "</tr>"
    return (
        '<div style="overflow-x:auto;border-radius:10px;border:1px solid #e0e0e0;overflow:hidden">'
        '<table style="border-collapse:collapse;width:100%;table-layout:fixed">'
        + _dag_header_html("#1565c0", "#1565c0")
        + f"<tbody>{rows}</tbody></table></div>"
    )


def cal_html_frivillig(mkey: str, my_shifts: list, open_days: list, closed_days: list, all_dates: list) -> str:
    """Kalender til frivillig-vagtplan: mine vagter=grøn, andres åbne=blå, lukket=rød."""
    y, m  = int(mkey[:4]), int(mkey[5:7])
    weeks = calendar.monthcalendar(y, m)
    rows  = ""
    for week in weeks:
        rows += "<tr>"
        for i, day in enumerate(week):
            if day == 0:
                rows += '<td style="background:#fafafa;border:1px solid #ececec;padding:8px"></td>'
                continue
            d_str   = date(y, m, day).isoformat()
            is_vdag = i in VAGTDAG_IDX
            is_mine = d_str in my_shifts
            is_open = d_str in open_days
            is_closed = d_str in closed_days

            if is_vdag:
                if is_mine:
                    bg, num_c, badge = "#c8e6c9", "#1b5e20", "✅ Din vagt"
                elif is_open:
                    bg, num_c, badge = "#e3f2fd", "#1565c0", "Åben"
                elif is_closed:
                    bg, num_c, badge = "#ffebee", "#b71c1c", "🔴 Lukket"
                else:
                    bg, num_c, badge = "#f5f5f5", "#aaa", ""
                rows += (
                    f'<td style="background:{bg};border:1px solid #ccc;'
                    f'padding:10px 4px;text-align:center;vertical-align:middle">'
                    f'<div style="font-size:20px;font-weight:800;color:{num_c}">{day}</div>'
                    f'<div style="font-size:10px;color:{num_c};margin-top:3px">{badge}</div>'
                    f'</td>'
                )
            else:
                rows += (
                    f'<td style="background:#fafafa;border:1px solid #ececec;'
                    f'padding:10px 4px;text-align:center;color:#ccc">'
                    f'<div style="font-size:14px">{day}</div></td>'
                )
        rows += "</tr>"
    return (
        '<div style="overflow-x:auto;border-radius:10px;border:1px solid #e0e0e0;overflow:hidden">'
        '<table style="border-collapse:collapse;width:100%;table-layout:fixed">'
        + _dag_header_html("#1565c0", "#1565c0")
        + f"<tbody>{rows}</tbody></table></div>"
    )

# ══════════════════════════════════════════════════════════════════════════════
#  INTERAKTIVE KALENDERE (klikbare)
# ══════════════════════════════════════════════════════════════════════════════
def _cal_header_cols(vagt_color: str, border_color: str):
    hcols = st.columns(7)
    for i, name in DAG_KORT.items():
        is_vd = i in VAGTDAG_IDX
        hcols[i].markdown(
            f'<div style="text-align:center;font-weight:700;font-size:13px;'
            f'padding:6px 0;letter-spacing:0.4px;'
            f'border-bottom:3px solid {"" if not is_vd else border_color};'
            f'color:{vagt_color if is_vd else "#ccc"}">'
            f'{name}</div>',
            unsafe_allow_html=True,
        )


def render_setup_kalender(mkey: str) -> list:
    """
    Klikbar opsætnings-kalender til administrator.
    Grøn = valgt vagtdag, Rød = fravalgt, Grå = ikke vagtdag.
    Returnerer sorteret liste af valgte dato-strenge.
    """
    y, m = int(mkey[:4]), int(mkey[5:7])
    sk   = f"setup_cal_{mkey}"
    if sk not in st.session_state:
        st.session_state[sk] = set(all_vagtdates(y, m))

    weeks = calendar.monthcalendar(y, m)
    _cal_header_cols("#2e7d32", "#2e7d32")

    for week in weeks:
        wcols = st.columns(7)
        for i, day in enumerate(week):
            with wcols[i]:
                if day == 0:
                    st.markdown('<div style="height:54px"></div>', unsafe_allow_html=True)
                    continue
                d_str   = date(y, m, day).isoformat()
                is_vdag = i in VAGTDAG_IDX
                if is_vdag:
                    is_sel = d_str in st.session_state[sk]
                    emoji  = "🟢" if is_sel else "🔴"
                    label  = f"{emoji} {day}"
                    if st.button(label, key=f"sc_{mkey}_{d_str}", use_container_width=True):
                        if is_sel:
                            st.session_state[sk].discard(d_str)
                        else:
                            st.session_state[sk].add(d_str)
                        st.rerun()
                else:
                    st.markdown(
                        f'<div style="text-align:center;color:#ddd;font-size:15px;'
                        f'padding:14px 0">{day}</div>',
                        unsafe_allow_html=True,
                    )

    return sorted(st.session_state[sk])


def render_pref_kalender(mkey: str, vid: str, released_set: set, existing: dict) -> dict:
    """
    Klikbar præference-kalender til frivillig.
    1 klik = 🟢 Ja, 2 klik = 🟡 Måske, 3 klik = tilbage til standard.
    Ikke-frigivne vagtdage er gråtonet.
    """
    y, m = int(mkey[:4]), int(mkey[5:7])
    sk   = f"vol_prefs_{mkey}_{vid}"
    if sk not in st.session_state:
        st.session_state[sk] = dict(existing)

    weeks = calendar.monthcalendar(y, m)
    _cal_header_cols("#1565c0", "#1565c0")

    for week in weeks:
        wcols = st.columns(7)
        for i, day in enumerate(week):
            with wcols[i]:
                if day == 0:
                    st.markdown('<div style="height:54px"></div>', unsafe_allow_html=True)
                    continue
                d_str   = date(y, m, day).isoformat()
                is_vdag = i in VAGTDAG_IDX
                is_rel  = d_str in released_set

                if is_vdag and is_rel:
                    state = st.session_state[sk].get(d_str, "")
                    if state == "sikker":
                        emoji = "🟢"
                    elif state == "måske":
                        emoji = "🟡"
                    else:
                        emoji = "⬜"
                    if st.button(f"{emoji} {day}", key=f"vpc_{mkey}_{vid}_{d_str}",
                                  use_container_width=True):
                        cur = st.session_state[sk].get(d_str, "")
                        st.session_state[sk][d_str] = (
                            "sikker" if cur == "" else
                            "måske"  if cur == "sikker" else ""
                        )
                        st.rerun()
                elif is_vdag and not is_rel:
                    st.markdown(
                        f'<div style="text-align:center;color:#ccc;font-size:15px;'
                        f'background:#f5f5f5;border-radius:8px;padding:13px 0;'
                        f'border:1px solid #eee">{day}</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        f'<div style="text-align:center;color:#e0e0e0;'
                        f'font-size:14px;padding:14px 0">{day}</div>',
                        unsafe_allow_html=True,
                    )

    return st.session_state[sk]

# ══════════════════════════════════════════════════════════════════════════════
#  FRIVILLIG-SIDE
# ══════════════════════════════════════════════════════════════════════════════
def side_frivillig(data: dict):
    if "vol_id" not in st.session_state:
        st.session_state.vol_id = None

    active_vols = {vid: v for vid, v in data["volunteers"].items() if v.get("active", True)}

    # ── Navnevalg-skærm ───────────────────────────────────────────────────────
    if st.session_state.vol_id is None:
        st.markdown("## 📅 Plexus Vagtplan")
        st.markdown("### 👋 Hvem er du?")
        st.markdown("Vælg dit navn for at se din vagtplan eller indsende ønsker.")
        if not active_vols:
            st.info("Ingen frivillige er oprettet endnu. Kontakt administratoren.")
            return
        navne = {v["name"]: vid
                 for vid, v in sorted(active_vols.items(), key=lambda x: x[1]["name"])}
        valgt = st.selectbox("", ["— Vælg dit navn —"] + list(navne.keys()),
                             label_visibility="collapsed")
        if valgt != "— Vælg dit navn —":
            st.session_state.vol_id = navne[valgt]
            st.rerun()
        return

    vid = st.session_state.vol_id
    if vid not in data["volunteers"]:
        st.session_state.vol_id = None
        st.rerun()

    vol = data["volunteers"][vid]

    # ── Header ────────────────────────────────────────────────────────────────
    col_name, col_btn = st.columns([5, 1])
    col_name.markdown(f"## 👋 Hej, {vol['name']}!")
    col_btn.markdown('<div style="margin-top:20px"></div>', unsafe_allow_html=True)
    if col_btn.button("← Skift", use_container_width=True):
        st.session_state.vol_id = None
        st.rerun()

    st.divider()

    # ── Find tilgængelige måneder ─────────────────────────────────────────────
    released_months = {k for k, c in data["monthly_config"].items() if c.get("released")}
    assigned_months = set(data.get("assignments", {}).keys())
    alle_måneder    = sorted(released_months | assigned_months, reverse=True)

    if not alle_måneder:
        st.info("📭 Ingen måneder er tilgængelige endnu. Tjek igen senere.")
        return

    sel_mk = st.selectbox("📅 Vælg periode", alle_måneder, index=0, format_func=mk_label)

    st.markdown("")

    if sel_mk in assigned_months:
        _vis_frivillig_vagtplan(data, vid, vol, sel_mk)
    elif sel_mk in released_months:
        _vis_frivillig_præferencer(data, vid, vol, sel_mk)
    else:
        st.info("Denne måned er ikke frigivet endnu.")


def _vis_frivillig_vagtplan(data: dict, vid: str, vol: dict, mkey: str):
    asgn      = data["assignments"][mkey]
    my_shifts = sorted(d for d, vs in asgn["shifts"].items() if vid in vs)
    kraevet   = vol.get("required_shifts", 2)

    c1, c2, c3 = st.columns(3)
    c1.metric("✅ Dine vagter", f"{len(my_shifts)}/{kraevet}")
    c2.metric("🟢 Åbningsdage", len(asgn["open"]))
    c3.metric("🔴 Lukkedage",   len(asgn["closed"]))

    st.markdown("### 📅 Vagtplan")
    st.markdown(
        cal_html_frivillig(mkey, my_shifts, asgn["open"], asgn["closed"],
                           data["monthly_config"].get(mkey, {}).get("dates", [])),
        unsafe_allow_html=True,
    )

    if my_shifts:
        st.markdown("---")
        st.markdown("**🗓️ Dine vagter:**")
        for d in my_shifts:
            st.success(f"  ✅ {fmt(d)}")
    else:
        st.info("Du er ikke tildelt vagter denne måned.")

    if len(my_shifts) < kraevet:
        st.warning(f"⚠️ Du fik {kraevet - len(my_shifts)} færre vagt(er) end aftalt.")


def _vis_frivillig_præferencer(data: dict, vid: str, vol: dict, mkey: str):
    cfg      = data["monthly_config"][mkey]
    rel_set  = set(cfg.get("dates", []))
    min_sel  = cfg.get("min_selections", 5)
    existing = data["preferences"].get(mkey, {}).get(vid, {})

    # Vis om der allerede er gemt
    already_saved = bool(data["preferences"].get(mkey, {}).get(vid))
    if already_saved:
        st.success("✅ Du har allerede gemt dine ønsker — du kan stadig ændre dem nedenfor.")

    st.markdown(f"### ✏️ Vagtønsker – {mk_label(mkey)}")
    st.markdown(
        f"Klik på datoerne for at markere dine ønsker.  \n"
        f"**🟢 = Ja** &nbsp;&nbsp; **🟡 = Måske** &nbsp;&nbsp; **⬜ = Ikke valgt**  \n"
        f"Vælg mindst **{min_sel}** datoer. Din månedlige kvote: **{vol.get('required_shifts', 2)} vagter**."
    )
    st.markdown("")

    prefs    = render_pref_kalender(mkey, vid, rel_set, existing)
    markeret = sum(1 for p in prefs.values() if p)
    nok      = markeret >= min_sel

    st.markdown("")
    ci, cb = st.columns([4, 1])
    if markeret == 0:
        ci.markdown("☝️ Klik på datoerne ovenfor for at markere dine ønsker.")
    elif nok:
        ci.markdown(f"✅ **{markeret}** datoer valgt — klar til at gemme!")
    else:
        ci.markdown(f"⚠️ **{markeret}** valgt — vælg mindst **{min_sel - markeret}** mere.")

    if cb.button("💾 Gem ønsker", type="primary", use_container_width=True, disabled=not nok):
        if mkey not in data["preferences"]:
            data["preferences"][mkey] = {}
        data["preferences"][mkey][vid] = {k: v for k, v in prefs.items() if v}
        save(data)
        st.success("✅ Dine ønsker er gemt! Du kan ændre dem igen når som helst, inden vagtplanen genereres.")
        st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
#  ADMIN-SIDE
# ══════════════════════════════════════════════════════════════════════════════
def side_admin(data: dict):
    if "admin_ok" not in st.session_state:
        st.session_state.admin_ok = False

    if not st.session_state.admin_ok:
        st.markdown("## 🔒 Administratorlogin")
        pwd = st.text_input("Adgangskode", type="password",
                            placeholder="Skriv adgangskode...")
        if st.button("🔓 Log ind", type="primary"):
            if pwd == data.get("admin_password", "plexus2024"):
                st.session_state.admin_ok = True
                st.rerun()
            else:
                st.error("❌ Forkert adgangskode.")
        return

    col_h, col_b = st.columns([5, 1])
    col_h.markdown("## ⚙️ Administration")
    if col_b.button("🚪 Log ud", use_container_width=True):
        st.session_state.admin_ok = False
        st.rerun()

    t1, t2, t3, t4 = st.tabs([
        "👥 Frivillige",
        "📅 Måneds-opsætning",
        "⚡ Vagttildeling",
        "📊 Resultater",
    ])
    with t1: _tab_frivillige(data)
    with t2: _tab_opstaetning(data)
    with t3: _tab_tildeling(data)
    with t4: _tab_resultater(data)


# ── Tab: Frivillige ───────────────────────────────────────────────────────────
def _tab_frivillige(data: dict):
    st.markdown("### 👥 Administrer frivillige")

    with st.expander("➕ Tilføj ny frivillig", expanded=not data["volunteers"]):
        with st.form("add_vol", clear_on_submit=True):
            c1, c2 = st.columns(2)
            navn  = c1.text_input("Navn")
            kvote = c2.number_input("Vagter pr. måned", 1, 20, 2)
            if st.form_submit_button("✅ Tilføj frivillig"):
                if navn.strip():
                    nid = str(data.get("next_id", 1))
                    data["volunteers"][nid] = {
                        "name": navn.strip(),
                        "required_shifts": int(kvote),
                        "active": True,
                    }
                    data["next_id"] = int(nid) + 1
                    save(data)
                    st.success(f"✅ {navn.strip()} er tilføjet!")
                    st.rerun()
                else:
                    st.warning("Angiv et navn.")

    if not data["volunteers"]:
        st.info("Ingen frivillige oprettet endnu.")
        return

    # Tabel
    st.markdown("")
    h1, h2, h3, h4 = st.columns([3, 2, 1, 1])
    h1.markdown("**Navn**"); h2.markdown("**Vagter/md.**"); h3.markdown("**Aktiv**")
    st.markdown("---")

    edits = {}
    for vid, vol in sorted(data["volunteers"].items(), key=lambda x: x[1]["name"]):
        c1, c2, c3, c4 = st.columns([3, 2, 1, 1])
        c1.markdown(f"**{vol['name']}**")
        q = c2.number_input("", 1, 20, vol.get("required_shifts", 2),
                             key=f"q_{vid}", label_visibility="collapsed")
        a = c3.checkbox("", vol.get("active", True),
                        key=f"a_{vid}", label_visibility="collapsed")
        edits[vid] = {"required_shifts": int(q), "active": a}
        if c4.button("🗑️", key=f"del_{vid}", help=f"Slet {vol['name']}"):
            del data["volunteers"][vid]
            save(data)
            st.rerun()

    st.markdown("")
    if st.button("💾 Gem alle ændringer", type="primary", use_container_width=True):
        for vid, vals in edits.items():
            if vid in data["volunteers"]:
                data["volunteers"][vid].update(vals)
        save(data)
        st.success("✅ Alle ændringer er gemt!")

    st.markdown("---")
    with st.expander("🔑 Skift admin-adgangskode"):
        with st.form("pwd_form"):
            p1 = st.text_input("Ny adgangskode", type="password")
            p2 = st.text_input("Gentag ny adgangskode", type="password")
            if st.form_submit_button("Gem adgangskode"):
                if p1 and p1 == p2:
                    data["admin_password"] = p1
                    save(data)
                    st.success("✅ Adgangskode er ændret.")
                else:
                    st.error("Adgangskoderne matcher ikke.")


# ── Tab: Måneds-opsætning ─────────────────────────────────────────────────────
def _tab_opstaetning(data: dict):
    st.markdown("### 📅 Måneds-opsætning")

    # Standard: måneden efter den seneste tildelte
    ny, nm = next_plan_month(data)

    c1, c2 = st.columns(2)
    år  = int(c1.number_input("År", 2024, 2030, ny))
    mdr = int(c2.selectbox("Måned", range(1, 13), index=nm - 1,
                             format_func=lambda x: MÅNEDER[x]))

    mkey   = mk(år, mdr)
    cfg    = data["monthly_config"].get(mkey, {})
    locked = cfg.get("released", False)

    st.markdown(f"#### {MÅNEDER[mdr]} {år}")
    st.markdown("---")

    if locked:
        st.success(f"✅ **{MÅNEDER[mdr]} {år}** er frigivet og låst for redigering.")
        col_info, col_revoke = st.columns([3, 1])
        col_info.markdown(
            f"- 📅 **Vagtdatoer:** {len(cfg.get('dates', []))} datoer  \n"
            f"- 👤 **Min. frivillige/vagt:** {cfg.get('min_per_shift', 3)}  \n"
            f"- 👥 **Max. frivillige/vagt:** {cfg.get('max_per_shift', 6)}  \n"
            f"- ☑️ **Min. ønsker/frivillig:** {cfg.get('min_selections', 5)}"
        )
        prefs_m = data["preferences"].get(mkey, {})
        aktive  = sum(1 for v in data["volunteers"].values() if v.get("active", True))
        st.info(f"📊 **{len(prefs_m)}/{aktive}** aktive frivillige har indsendt ønsker.")

        # Tilbagekald-knap med bekræftelse
        st.markdown("")
        if "confirm_revoke" not in st.session_state:
            st.session_state.confirm_revoke = None

        if st.button("🔓 Tilbagekald frigivelse", use_container_width=True):
            st.session_state.confirm_revoke = mkey

        if st.session_state.confirm_revoke == mkey:
            st.error(
                "⚠️ **Advarsel!** Dette vil tilbagekalde frigivelsen og slette **alle indsendte ønsker** "
                f"for **{MÅNEDER[mdr]} {år}**. Eventuelle tildelte vagter slettes også. "
                "Du kan frigive måneden igen bagefter. Er du sikker?"
            )
            ck1, ck2 = st.columns(2)
            if ck1.button("✅ Ja, tilbagekald", type="primary", use_container_width=True):
                data["monthly_config"][mkey]["released"] = False
                data["preferences"].pop(mkey, None)
                data["assignments"].pop(mkey, None)
                # Nulstil session state for kalender
                sk = f"setup_cal_{mkey}"
                st.session_state.pop(sk, None)
                st.session_state.confirm_revoke = None
                save(data)
                st.success("✅ Frigivelse tilbagekaldt.")
                st.rerun()
            if ck2.button("❌ Annuller", use_container_width=True):
                st.session_state.confirm_revoke = None
                st.rerun()
        return

    # ── Opsætningsformular ────────────────────────────────────────────────────
    st.markdown("**🗓️ Klik på vagtdatoerne for at aktivere/deaktivere dem:**")
    st.caption("🟢 = Aktiv vagtdag &nbsp;&nbsp; 🔴 = Fravalgt &nbsp;&nbsp; Grå = ikke en vagtdag")
    st.markdown("")

    selected = render_setup_kalender(mkey)

    st.markdown("---")
    c3, c4, c5 = st.columns(3)
    min_per = c3.number_input("👤 Min. frivillige/vagt", 1, 10, cfg.get("min_per_shift", 3))
    max_per = c4.number_input("👥 Max. frivillige/vagt", 1, 20, cfg.get("max_per_shift", 6))
    min_sel = c5.number_input("☑️ Min. ønsker/frivillig", 1, 20, cfg.get("min_selections", 5))

    st.markdown("")
    cs, cr = st.columns(2)

    if cs.button("💾 Gem opsætning (ikke frigivet endnu)", use_container_width=True):
        data["monthly_config"][mkey] = {
            "dates": selected,
            "min_per_shift": int(min_per),
            "max_per_shift": int(max_per),
            "min_selections": int(min_sel),
            "released": False,
        }
        save(data)
        st.success(f"✅ Opsætning for {MÅNEDER[mdr]} {år} er gemt.")

    if cr.button("🚀 Frigiv til frivillige", type="primary", use_container_width=True):
        if not selected:
            st.error("Vælg mindst én aktiv vagtdato, inden du frigiver.")
        else:
            data["monthly_config"][mkey] = {
                "dates": selected,
                "min_per_shift": int(min_per),
                "max_per_shift": int(max_per),
                "min_selections": int(min_sel),
                "released": True,
            }
            save(data)
            st.success(f"🎉 **{MÅNEDER[mdr]} {år}** er nu frigivet til de frivillige!")
            st.rerun()

    prefs_m = data["preferences"].get(mkey, {})
    aktive  = sum(1 for v in data["volunteers"].values() if v.get("active", True))
    if aktive:
        st.info(f"📊 **{len(prefs_m)}/{aktive}** aktive frivillige har indsendt ønsker.")


# ── Tab: Vagttildeling ────────────────────────────────────────────────────────
def _tab_tildeling(data: dict):
    st.markdown("### ⚡ Automatisk vagttildeling")

    frigivne = sorted(k for k, c in data["monthly_config"].items() if c.get("released"))
    if not frigivne:
        st.warning("📭 Ingen måneder er frigivet endnu.")
        return

    mkey    = st.selectbox("Vælg måned", frigivne, format_func=mk_label)
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
                st.write(f"• {v['name']}  *(Ja: {s} / Måske: {ms})*")
    with col_nej:
        st.markdown("**❌ Mangler endnu:**")
        for vid, v in aktive.items():
            if vid not in prefs_m:
                st.write(f"• {v['name']}")

    st.markdown("---")

    allerede = mkey in data.get("assignments", {})
    if allerede:
        st.warning("⚠️ Vagter er allerede tildelt for denne måned. Klik nedenfor for at køre forfra og overskrive.")

    if st.button("🚀 Tildel vagter automatisk", type="primary", use_container_width=True):
        if not prefs_m:
            st.error("Ingen frivillige har indsendt ønsker endnu.")
        else:
            data = auto_assign(data, mkey)
            save(data)
            st.success("🎉 Vagter er tildelt!")
            st.balloons()
            st.rerun()


# ── Tab: Resultater ───────────────────────────────────────────────────────────
def _tab_resultater(data: dict):
    st.markdown("### 📊 Resultater")

    tildelte = sorted(data.get("assignments", {}).keys(), reverse=True)
    if not tildelte:
        st.info("📭 Ingen vagter er tildelt endnu.")
        return

    mkey = st.selectbox("Vælg måned", tildelte, format_func=mk_label)
    asgn = data["assignments"][mkey]
    vols = data["volunteers"]

    st.caption(f"⏱️ Genereret: {asgn.get('generated_at', '–')}")

    åbne    = len(asgn["open"])
    lukkede = len(asgn["closed"])
    total   = åbne + lukkede
    pct     = round(100 * åbne / total) if total > 0 else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("🟢 Åbningsdage",   åbne)
    c2.metric("🔴 Lukkedage",     lukkede)
    c3.metric("📈 Åbningsprocent", f"{pct}%")

    if asgn.get("unmet_quota"):
        with st.expander("⚠️ Frivillige med ufyldt kvote"):
            for vid, mangler in asgn["unmet_quota"].items():
                st.write(f"• **{vols.get(vid, {}).get('name', vid)}** mangler {mangler} vagt(er)")

    st.markdown("### 📅 Kalender-oversigt")
    st.markdown(cal_html_resultater(mkey, asgn["shifts"], asgn["open"], vols),
                unsafe_allow_html=True)

    st.markdown("")
    with st.expander("👤 Oversigt per frivillig"):
        for vid, vol in sorted(vols.items(), key=lambda x: x[1]["name"]):
            if not vol.get("active"):
                continue
            mine    = sorted(d for d, vs in asgn["shifts"].items() if vid in vs)
            kraevet = vol.get("required_shifts", 2)
            ikon    = "✅" if len(mine) >= kraevet else "⚠️"
            st.markdown(f"**{ikon} {vol['name']}** — {len(mine)}/{kraevet} vagter")
            for d in mine:
                st.write(f"  • {fmt(d)}")
            if len(mine) < kraevet:
                st.caption(f"  Fik {kraevet - len(mine)} færre end aftalt.")

    # CSV-eksport
    rækker = ["Dato,Status,Frivillige"]
    for d in sorted(asgn["shifts"]):
        navne  = "; ".join(vols[v]["name"] for v in asgn["shifts"][d] if v in vols)
        status = "Åben" if d in asgn["open"] else "Lukket"
        rækker.append(f"{fmt(d)},{status},{navne}")

    st.markdown("")
    st.download_button(
        "⬇️ Download vagtplan som CSV",
        "\n".join(rækker).encode("utf-8-sig"),
        f"plexus_vagtplan_{mkey}.csv",
        "text/csv",
        use_container_width=True,
    )

# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    st.set_page_config(
        page_title="Plexus Vagtplan",
        page_icon="📅",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(CSS, unsafe_allow_html=True)
    data = load()

    with st.sidebar:
        st.markdown("## 📅 Plexus Vagtplan")
        st.divider()
        side = st.radio(
            "Navigation",
            ["🙋 Frivillig", "⚙️ Administrator"],
            label_visibility="hidden",
        )
        st.divider()
        st.caption(f"Version {VERSION}")
        st.caption("Lavet af Fabian Salvatore")

    if side == "🙋 Frivillig":
        side_frivillig(data)
    else:
        side_admin(data)


if __name__ == "__main__":
    main()

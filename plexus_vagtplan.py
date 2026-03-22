"""
Plexus Vagtplan – Vagtønske og automatisk vagttildeling
Run med: streamlit run plexus_vagtplan.py
"""

import streamlit as st
import json
import os
import calendar
from datetime import date, datetime
from collections import defaultdict

# ── Side-konfiguration ─────────────────────────────────────────────────────
st.set_page_config(
    page_title="Plexus Vagtplan",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Konstanter ─────────────────────────────────────────────────────────────
DATA_FILE = "plexus_data.json"

VAGTDAGE = {0: "Mandag", 1: "Tirsdag", 2: "Onsdag", 6: "Søndag"}   # ugedage der er åbne
UGEDAGE_DK = ["Man", "Tirs", "Ons", "Tors", "Fre", "Lør", "Søn"]
MÅNEDER_DK = [
    "", "Januar", "Februar", "Marts", "April", "Maj", "Juni",
    "Juli", "August", "September", "Oktober", "November", "December"
]

CSS = """
<style>
section[data-testid="stSidebar"] { min-width: 220px !important; max-width: 240px !important; }
div[data-testid="stMetric"] { background: #f8f9fa; border-radius: 8px; padding: 12px 16px; }
.status-open  { display:inline-block; background:#dcfce7; color:#166534;
                border-radius:6px; padding:2px 10px; font-size:0.82rem; font-weight:500; }
.status-closed{ display:inline-block; background:#fee2e2; color:#991b1b;
                border-radius:6px; padding:2px 10px; font-size:0.82rem; font-weight:500; }
.badge-sikker { display:inline-block; background:#22c55e; color:#fff;
                border-radius:6px; padding:1px 8px; font-size:0.78rem; }
.badge-måske  { display:inline-block; background:#f59e0b; color:#fff;
                border-radius:6px; padding:1px 8px; font-size:0.78rem; }
</style>
"""

# ── Data-hjælpere ──────────────────────────────────────────────────────────

def load_data() -> dict:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "volunteers": {},           # {id: {name, required_shifts, active}}
        "monthly_config": {},       # {month_key: {dates, min_per_shift, min_selections, released}}
        "preferences": {},          # {month_key: {vol_id: {date: "sikker"/"måske"}}}
        "assignments": {},          # {month_key: {shifts, open, closed, unmet_quota, generated_at}}
        "admin_password": "plexus2024",
        "next_vol_id": 1,
    }


def save_data(data: dict):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def month_key(year: int, month: int) -> str:
    return f"{year}-{month:02d}"


def month_label(mk: str) -> str:
    y, m = mk.split("-")
    return f"{MÅNEDER_DK[int(m)]} {y}"


def vagtdatoer(year: int, month: int) -> list[str]:
    """Returnerer alle Man/Tirs/Ons/Søn-datoer i måneden som ISO-strenge."""
    n = calendar.monthrange(year, month)[1]
    return [
        date(year, month, d).isoformat()
        for d in range(1, n + 1)
        if date(year, month, d).weekday() in VAGTDAGE
    ]


def fmt_dato(d_str: str) -> str:
    d = date.fromisoformat(d_str)
    return f"{VAGTDAGE[d.weekday()]} {d.day}/{d.month}"


# ── Fordelingsalgoritme ────────────────────────────────────────────────────

def auto_assign(data: dict, mk: str) -> dict:
    """
    Fordeler vagter for at maksimere åbningsdage.
    Prioriterer 'Helt sikker' over 'Måske'.
    Fylder resterende kvote op bagefter.
    """
    config = data["monthly_config"].get(mk, {})
    dates = config.get("dates", [])
    min_per = config.get("min_per_shift", 1)
    prefs_data = data["preferences"].get(mk, {})
    vols = data["volunteers"]

    active = [vid for vid, v in vols.items() if v.get("active", True)]

    # Præference-matrix: 2=sikker, 1=måske, 0=ingen
    prio = {
        vid: {
            d: (2 if prefs_data.get(vid, {}).get(d) == "sikker"
                else 1 if prefs_data.get(vid, {}).get(d) == "måske"
                else 0)
            for d in dates
        }
        for vid in active
    }

    required = {vid: vols[vid].get("required_shifts", 4) for vid in active}
    remaining = dict(required)
    shifts: dict[str, list] = {d: [] for d in dates}

    # Sorter datoer efter scarcity – sværest at besætte først
    def urgency(d):
        return sum(1 for v in active if prio[v][d] > 0)

    sorted_dates = sorted(dates, key=urgency)

    # Fase 1: Forsøg at åbne hver dag (opnå min_per_shift dækning)
    for d in sorted_dates:
        candidates = [
            vid for vid in active
            if prio[vid][d] > 0 and remaining[vid] > 0 and vid not in shifts[d]
        ]
        candidates.sort(key=lambda v: (prio[v][d], remaining[v]), reverse=True)
        assigned = 0
        for vid in candidates:
            if assigned >= min_per:
                break
            shifts[d].append(vid)
            remaining[vid] -= 1
            assigned += 1

    # Fase 2: Fyld resterende kvote med frivilligens ønsker
    for vid in sorted(active, key=lambda v: remaining[v], reverse=True):
        while remaining[vid] > 0:
            cands = [
                d for d in dates
                if prio[vid][d] > 0 and vid not in shifts[d]
            ]
            if not cands:
                break
            # Foretruk dage der ellers er tomme (for at åbne flest mulige)
            cands.sort(key=lambda d: (len(shifts[d]), -prio[vid][d]))
            shifts[cands[0]].append(vid)
            remaining[vid] -= 1

    open_days = [d for d in dates if len(shifts[d]) >= min_per]
    closed_days = [d for d in dates if len(shifts[d]) < min_per]

    data["assignments"][mk] = {
        "shifts": shifts,
        "open": open_days,
        "closed": closed_days,
        "unmet_quota": {vid: remaining[vid] for vid in active if remaining[vid] > 0},
        "generated_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
    }
    return data


# ── App-sider ──────────────────────────────────────────────────────────────

def side_frivillig(data: dict):
    st.header("Mine vagtønsker")

    active_vols = {vid: v for vid, v in data["volunteers"].items() if v.get("active", True)}
    if not active_vols:
        st.info("Ingen frivillige er oprettet endnu. Kontakt administratoren.")
        return

    col1, col2 = st.columns([2, 2])
    with col1:
        navn_til_id = {v["name"]: vid for vid, v in sorted(active_vols.items(), key=lambda x: x[1]["name"])}
        valgt_navn = st.selectbox("Vælg dit navn", ["— Vælg —"] + list(navn_til_id.keys()))
    if valgt_navn == "— Vælg —":
        st.info("Vælg dit navn ovenfor for at komme i gang.")
        return

    vid = navn_til_id[valgt_navn]
    vol = data["volunteers"][vid]

    # Kun frigivne måneder
    frigivne = sorted(mk for mk, c in data["monthly_config"].items() if c.get("released"))
    if not frigivne:
        st.warning("Ingen vagter er frigivet endnu. Tjek igen senere.")
        return

    with col2:
        valgt_mk = st.selectbox("Måned", frigivne, format_func=month_label)

    config = data["monthly_config"][valgt_mk]
    dates = config.get("dates", [])
    min_valg = config.get("min_selections", 5)

    # Vis egne tildelte vagter hvis fordeling er kørt
    if valgt_mk in data.get("assignments", {}):
        st.success("✅ Vagterne for denne måned er tildelt!")
        assignment = data["assignments"][valgt_mk]
        mine = sorted(d for d, vols in assignment["shifts"].items() if vid in vols)
        if mine:
            st.subheader(f"Dine vagter – {month_label(valgt_mk)}")
            for d in mine:
                st.write(f"✅ {fmt_dato(d)}")
        else:
            st.info("Du er ikke tildelt vagter denne måned.")
        return

    existing = data["preferences"].get(valgt_mk, {}).get(vid, {})

    st.subheader(f"Vælg ønsker – {month_label(valgt_mk)}")
    st.caption(
        f"Markér mindst **{min_valg}** datoer. "
        f"Din aftalte månedlige kvote: **{vol.get('required_shifts', 4)} vagter**."
    )

    # Præference-valgmuligheder
    VALG = {"Ingen": "", "Måske": "måske", "Helt sikker": "sikker"}
    VALG_REV = {v: k for k, v in VALG.items()}

    nye_prefs: dict[str, str] = dict(existing)

    # Gruppér datoer efter uge
    uger: dict[int, list] = defaultdict(list)
    for d_str in sorted(dates):
        uge = date.fromisoformat(d_str).isocalendar()[1]
        uger[uge].append(d_str)

    for uge_nr, uge_datoer in sorted(uger.items()):
        cols = st.columns(len(uge_datoer))
        for i, d_str in enumerate(uge_datoer):
            d = date.fromisoformat(d_str)
            current = existing.get(d_str, "")
            with cols[i]:
                st.markdown(f"**{VAGTDAGE[d.weekday()]}**  \n{d.day}/{d.month}")
                valg = st.radio(
                    label=d_str,
                    options=list(VALG.keys()),
                    index=list(VALG.values()).index(current) if current in VALG.values() else 0,
                    key=f"pref_{valgt_mk}_{d_str}",
                    label_visibility="collapsed",
                    horizontal=False,
                )
                nye_prefs[d_str] = VALG[valg]

    markeret = sum(1 for p in nye_prefs.values() if p)
    nok = markeret >= min_valg

    st.divider()
    col_info, col_btn = st.columns([3, 1])
    with col_info:
        farve = "green" if nok else "red"
        st.markdown(f":{farve}[**{markeret}** datoer valgt (minimum {min_valg})]")
    with col_btn:
        if st.button("💾 Gem ønsker", type="primary", disabled=not nok):
            if valgt_mk not in data["preferences"]:
                data["preferences"][valgt_mk] = {}
            data["preferences"][valgt_mk][vid] = {k: v for k, v in nye_prefs.items() if v}
            save_data(data)
            st.success("Dine ønsker er gemt! ✅")
            st.rerun()

    if not nok:
        st.warning(f"⚠️ Vælg mindst {min_valg - markeret} dato(er) mere for at gemme.")


# ── ADMIN ──────────────────────────────────────────────────────────────────

def side_admin(data: dict):
    if "admin_ok" not in st.session_state:
        st.session_state.admin_ok = False

    if not st.session_state.admin_ok:
        st.header("🔒 Administratorlogin")
        pwd = st.text_input("Adgangskode", type="password")
        if st.button("Log ind", type="primary"):
            if pwd == data["admin_password"]:
                st.session_state.admin_ok = True
                st.rerun()
            else:
                st.error("Forkert adgangskode.")
        return

    with st.sidebar:
        if st.button("🚪 Log ud"):
            st.session_state.admin_ok = False
            st.rerun()

    st.header("⚙️ Administration")

    t1, t2, t3, t4 = st.tabs(
        ["👥 Frivillige", "📅 Måneds-opsætning", "⚡ Vagttildeling", "📊 Resultater"]
    )
    with t1:
        tab_frivillige(data)
    with t2:
        tab_måneds_opsætning(data)
    with t3:
        tab_tildeling(data)
    with t4:
        tab_resultater(data)


def tab_frivillige(data: dict):
    st.subheader("Administrer frivillige")

    # Tilføj frivillig
    with st.expander("➕ Tilføj ny frivillig", expanded=not data["volunteers"]):
        with st.form("add_vol", clear_on_submit=True):
            c1, c2 = st.columns(2)
            navn = c1.text_input("Navn")
            kvote = c2.number_input("Vagter pr. måned", 1, 20, 4)
            if st.form_submit_button("Tilføj"):
                if navn.strip():
                    new_id = str(data.get("next_vol_id", 1))
                    data["volunteers"][new_id] = {
                        "name": navn.strip(),
                        "required_shifts": int(kvote),
                        "active": True,
                    }
                    data["next_vol_id"] = int(new_id) + 1
                    save_data(data)
                    st.success(f"✅ {navn} er tilføjet!")
                    st.rerun()
                else:
                    st.warning("Angiv et navn.")

    if not data["volunteers"]:
        st.info("Ingen frivillige endnu.")
        return

    st.subheader("Nuværende frivillige")
    st.caption("Gem efter ændringer på hver linje.")

    # Tabel-header
    h1, h2, h3, h4 = st.columns([3, 2, 1, 1])
    h1.markdown("**Navn**"); h2.markdown("**Vagter/md.**"); h3.markdown("**Aktiv**")

    for vid, vol in sorted(data["volunteers"].items(), key=lambda x: x[1]["name"]):
        c1, c2, c3, c4 = st.columns([3, 2, 1, 1])
        c1.write(vol["name"])
        new_q = c2.number_input("", 1, 20, vol.get("required_shifts", 4),
                                 key=f"q_{vid}", label_visibility="collapsed")
        new_a = c3.checkbox("", vol.get("active", True), key=f"a_{vid}",
                             label_visibility="collapsed")
        if c4.button("Gem", key=f"s_{vid}"):
            data["volunteers"][vid]["required_shifts"] = int(new_q)
            data["volunteers"][vid]["active"] = new_a
            save_data(data)
            st.toast(f"✅ {vol['name']} opdateret")

    # Skift admin-adgangskode
    with st.expander("🔑 Skift adgangskode"):
        with st.form("change_pwd"):
            np1 = st.text_input("Ny adgangskode", type="password")
            np2 = st.text_input("Gentag ny adgangskode", type="password")
            if st.form_submit_button("Skift"):
                if np1 and np1 == np2:
                    data["admin_password"] = np1
                    save_data(data)
                    st.success("Adgangskode ændret.")
                else:
                    st.error("Adgangskoderne stemmer ikke overens.")


def tab_måneds_opsætning(data: dict):
    st.subheader("Måneds-opsætning")

    now = datetime.now()
    c1, c2 = st.columns(2)
    år = c1.number_input("År", 2024, 2030, now.year)
    mdr = c2.selectbox("Måned", range(1, 13), index=now.month - 1,
                        format_func=lambda x: MÅNEDER_DK[x])

    mk = month_key(int(år), int(mdr))
    alle_datoer = vagtdatoer(int(år), int(mdr))
    existing = data["monthly_config"].get(mk, {})
    valgte = set(existing.get("dates", alle_datoer))

    st.markdown(f"**Datoer (Man/Tirs/Ons/Søn) i {MÅNEDER_DK[int(mdr)]} {int(år)}:**")
    st.caption("Fravælg datoer der ikke skal være vagter (helligdage, lukket osv.)")

    checked: list[str] = []
    cols = st.columns(4)
    for i, d_str in enumerate(alle_datoer):
        with cols[i % 4]:
            if st.checkbox(fmt_dato(d_str), value=d_str in valgte, key=f"dc_{mk}_{d_str}"):
                checked.append(d_str)

    st.divider()
    c3, c4, c5 = st.columns(3)
    min_per = c3.number_input("Min. frivillige pr. vagt", 1, 10,
                               existing.get("min_per_shift", 1))
    min_sel = c4.number_input("Min. ønsker pr. frivillig", 1, 20,
                               existing.get("min_selections", 5))
    frigivet = c5.checkbox("Frigiv til frivillige", existing.get("released", False))

    if st.button("💾 Gem opsætning", type="primary"):
        data["monthly_config"][mk] = {
            "dates": sorted(checked),
            "min_per_shift": int(min_per),
            "min_selections": int(min_sel),
            "released": frigivet,
        }
        save_data(data)
        st.success(f"✅ Opsætning for {MÅNEDER_DK[int(mdr)]} {int(år)} gemt!")

    # Hvem har indsendt
    if mk in data.get("preferences", {}):
        indsendt = len(data["preferences"][mk])
        aktive = sum(1 for v in data["volunteers"].values() if v.get("active"))
        st.info(f"📊 **{indsendt}/{aktive}** aktive frivillige har indsendt ønsker.")


def tab_tildeling(data: dict):
    st.subheader("Automatisk vagttildeling")

    frigivne = sorted(mk for mk, c in data["monthly_config"].items() if c.get("released"))
    if not frigivne:
        st.warning("Ingen måneder er frigivet endnu.")
        return

    valgt_mk = st.selectbox("Vælg måned", frigivne, format_func=month_label)
    prefs_data = data["preferences"].get(valgt_mk, {})
    aktive = {vid: v for vid, v in data["volunteers"].items() if v.get("active")}

    indsendt = len(prefs_data)
    total = len(aktive)

    c1, c2 = st.columns(2)
    c1.metric("Har indsendt ønsker", f"{indsendt}/{total}")

    # Vis status per frivillig
    col_ja, col_nej = st.columns(2)
    with col_ja:
        st.markdown("**Klar ✅**")
        for vid, v in aktive.items():
            if vid in prefs_data:
                n = sum(1 for p in prefs_data[vid].values() if p == "sikker")
                m = sum(1 for p in prefs_data[vid].values() if p == "måske")
                st.write(f"• {v['name']} *(sikker: {n}, måske: {m})*")
    with col_nej:
        st.markdown("**Mangler ❌**")
        for vid, v in aktive.items():
            if vid not in prefs_data:
                st.write(f"• {v['name']}")

    st.divider()

    allerede = valgt_mk in data.get("assignments", {})
    if allerede:
        st.warning("⚠️ Vagter er allerede tildelt – klik nedenfor for at køre igen og overskrive.")

    if st.button("🚀 Tildel vagter automatisk", type="primary", disabled=indsendt == 0):
        data = auto_assign(data, valgt_mk)
        save_data(data)
        st.success("✅ Vagter tildelt!")
        st.rerun()

    if indsendt == 0:
        st.error("Ingen frivillige har indsendt ønsker endnu.")


def tab_resultater(data: dict):
    st.subheader("Resultater")

    tildelte = list(data.get("assignments", {}).keys())
    if not tildelte:
        st.info("Ingen vagter tildelt endnu.")
        return

    valgt_mk = st.selectbox("Vælg måned", sorted(tildelte, reverse=True), format_func=month_label)
    assignment = data["assignments"][valgt_mk]
    vols = data["volunteers"]
    config = data["monthly_config"].get(valgt_mk, {})

    st.caption(f"Genereret: {assignment.get('generated_at', '–')}")

    # Nøgletal
    åbne = len(assignment["open"])
    lukkede = len(assignment["closed"])
    total = åbne + lukkede
    pct = round(100 * åbne / total) if total > 0 else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("🟢 Åbningsdage", åbne)
    c2.metric("🔴 Lukkedage", lukkede)
    c3.metric("Åbningsprocent", f"{pct}%")

    if assignment.get("unmet_quota"):
        with st.expander("⚠️ Frivillige med ufyldt kvote"):
            for vid, mangler in assignment["unmet_quota"].items():
                navn = vols.get(vid, {}).get("name", vid)
                st.write(f"• **{navn}** mangler **{mangler}** vagt(er)")

    t_kal, t_vol, t_csv = st.tabs(["📅 Kalender-oversigt", "👤 Per frivillig", "⬇️ Eksport"])

    with t_kal:
        dates = config.get("dates", sorted(assignment["shifts"].keys()))
        for d_str in sorted(dates):
            er_åben = d_str in assignment["open"]
            vagthavende = assignment["shifts"].get(d_str, [])
            navne = [vols[vid]["name"] for vid in vagthavende if vid in vols]

            c_dato, c_status, c_navne = st.columns([2, 1, 4])
            c_dato.write(fmt_dato(d_str))
            if er_åben:
                c_status.markdown('<span class="status-open">Åben</span>', unsafe_allow_html=True)
            else:
                c_status.markdown('<span class="status-closed">Lukket</span>', unsafe_allow_html=True)
            c_navne.write(", ".join(navne) if navne else "—")

    with t_vol:
        for vid, vol in sorted(vols.items(), key=lambda x: x[1]["name"]):
            if not vol.get("active"):
                continue
            mine = sorted(d for d, vs in assignment["shifts"].items() if vid in vs)
            krævet = vol.get("required_shifts", 4)
            fik = len(mine)
            label = f"{vol['name']}  —  {fik}/{krævet} vagter"
            with st.expander(label):
                if mine:
                    for d in mine:
                        st.write(f"• {fmt_dato(d)}")
                else:
                    st.write("Ingen vagter tildelt.")
                if fik < krævet:
                    st.warning(f"Fik {krævet - fik} færre vagt(er) end aftalt.")

    with t_csv:
        st.markdown("**Download oversigt som CSV**")
        rows = []
        for d_str in sorted(assignment["shifts"].keys()):
            vagthavende = assignment["shifts"].get(d_str, [])
            navne = "; ".join(vols[vid]["name"] for vid in vagthavende if vid in vols)
            status = "Åben" if d_str in assignment["open"] else "Lukket"
            rows.append(f"{fmt_dato(d_str)},{status},{navne}")

        csv_tekst = "Dato,Status,Frivillige\n" + "\n".join(rows)
        st.download_button(
            "⬇️ Download CSV",
            data=csv_tekst.encode("utf-8-sig"),
            file_name=f"plexus_vagtplan_{valgt_mk}.csv",
            mime="text/csv",
        )


# ── Hoved-app ──────────────────────────────────────────────────────────────

def main():
    st.markdown(CSS, unsafe_allow_html=True)
    data = load_data()

    with st.sidebar:
        st.markdown("## 📅 Plexus Vagtplan")
        st.divider()
        side = st.radio(
            "Navigation",
            ["🙋 Frivillig portal", "⚙️ Administrator"],
            label_visibility="hidden",
        )

    if side == "🙋 Frivillig portal":
        side_frivillig(data)
    else:
        side_admin(data)


if __name__ == "__main__":
    main()

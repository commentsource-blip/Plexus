"""
Plexus Vagtplan
Lavet af Fabian Salvatore
"""
import streamlit as st
import json, os, calendar
from datetime import date, datetime
from collections import defaultdict

# ── Konfiguration ─────────────────────────────────────────────────────────────
VERSION      = date.today().strftime("%d.%m.%Y")
DATA_FILE    = "plexus_data.json"
VAGTDAG_IDX  = {0, 1, 2, 6}   # Man=0, Tirs=1, Ons=2, Son=6
DAGNAVNE     = {0:"Man", 1:"Tirs", 2:"Ons", 3:"Tor", 4:"Fre", 5:"Lor", 6:"Son"}
MANEDER      = ["","Januar","Februar","Marts","April","Maj","Juni",
                "Juli","August","September","Oktober","November","December"]

# ── Data-hjaelpere ────────────────────────────────────────────────────────────
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

def mk(y, m)       -> str: return f"{y}-{m:02d}"
def mk_label(k)    -> str: y, m = k.split("-"); return f"{MANEDER[int(m)]} {y}"

def all_vagtdates(y, m) -> list:
    n = calendar.monthrange(y, m)[1]
    return [date(y, m, d).isoformat()
            for d in range(1, n + 1)
            if date(y, m, d).weekday() in VAGTDAG_IDX]

def fmt(d_str: str) -> str:
    d = date.fromisoformat(d_str)
    dag_dk = {0:"Mandag",1:"Tirsdag",2:"Onsdag",6:"Sondag"}
    return f"{dag_dk.get(d.weekday(), DAGNAVNE[d.weekday()])} {d.day}/{d.month}"

# ── Fordelingsalgoritme ───────────────────────────────────────────────────────
def auto_assign(data: dict, mkey: str) -> dict:
    cfg      = data["monthly_config"].get(mkey, {})
    dates    = cfg.get("dates", [])
    min_per  = cfg.get("min_per_shift", 1)
    max_per  = cfg.get("max_per_shift", 5)
    prefs_m  = data["preferences"].get(mkey, {})
    vols     = data["volunteers"]
    active   = [vid for vid, v in vols.items() if v.get("active", True)]

    prio = {
        vid: {
            d: (2 if prefs_m.get(vid, {}).get(d) == "sikker"
                else 1 if prefs_m.get(vid, {}).get(d) == "maske"
                else 0)
            for d in dates
        }
        for vid in active
    }
    remaining = {vid: vols[vid].get("required_shifts", 2) for vid in active}
    shifts    = {d: [] for d in dates}

    sorted_dates = sorted(dates, key=lambda d: sum(1 for v in active if prio[v][d] > 0))

    # Fase 1a: min_per_shift med "Ja" (prio=2) forst
    # Fase 1b: supplér med "Maske" (prio=1)
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

# ── HTML-kalendre (kun visning) ───────────────────────────────────────────────
def _cal_header_html(vagtdag_color: str, other_color: str, border_color: str) -> str:
    dag_labels = ["Man","Tirs","Ons","Tor","Fre","Lor","Son"]
    cells = ""
    for i, name in enumerate(dag_labels):
        is_vd = i in VAGTDAG_IDX
        cells += (
            f'<th style="padding:8px 4px;font-size:13px;font-weight:600;'
            f'border:1px solid #e0e0e0;'
            f'background:{"#f0f7ff" if is_vd else "#f9f9f9"};'
            f'color:{vagtdag_color if is_vd else other_color};'
            f'border-bottom:3px solid {border_color if is_vd else "#e0e0e0"}">'
            f'{name}</th>'
        )
    return f"<thead><tr>{cells}</tr></thead>"


def cal_html_results(mkey: str, shifts: dict, open_days: list, vols: dict) -> str:
    y, m = int(mkey[:4]), int(mkey[5:7])
    weeks = calendar.monthcalendar(y, m)
    rows_html = ""
    for week in weeks:
        rows_html += "<tr>"
        for i, day in enumerate(week):
            if day == 0:
                rows_html += '<td style="background:#fafafa;border:1px solid #e8e8e8;padding:6px"></td>'
                continue
            d_str   = date(y, m, day).isoformat()
            is_vdag = i in VAGTDAG_IDX
            is_open = d_str in open_days
            navne   = [vols[v]["name"] for v in shifts.get(d_str, []) if v in vols]

            if is_vdag:
                bg    = "#e8f5e9" if is_open else "#ffebee"
                badge = "Aben" if is_open else "Lukket"
                dot   = "&#128994;" if is_open else "&#128308;"
                names_html = "".join(
                    f'<div style="font-size:11px;color:#333;margin-top:3px;'
                    f'background:#ffffffcc;border-radius:3px;padding:1px 5px">{n}</div>'
                    for n in navne
                )
                rows_html += (
                    f'<td style="background:{bg};border:1px solid #ccc;'
                    f'padding:7px 5px;vertical-align:top;min-width:80px">'
                    f'<div style="font-weight:700;font-size:17px;color:#222">{day}</div>'
                    f'<div style="font-size:10px;color:#555;margin-bottom:3px">{dot} {badge}</div>'
                    f'{names_html}</td>'
                )
            else:
                rows_html += (
                    f'<td style="background:#fafafa;border:1px solid #e8e8e8;'
                    f'padding:7px 5px;text-align:center;color:#ccc;vertical-align:top">'
                    f'<div style="font-size:14px">{day}</div></td>'
                )
        rows_html += "</tr>"

    return (
        '<div style="overflow-x:auto">'
        '<table style="border-collapse:collapse;width:100%;table-layout:fixed">'
        + _cal_header_html("#1565c0", "#bbb", "#1565c0")
        + f"<tbody>{rows_html}</tbody></table></div>"
    )


def cal_html_vagtplan(mkey: str, my_shifts: list) -> str:
    y, m = int(mkey[:4]), int(mkey[5:7])
    weeks = calendar.monthcalendar(y, m)
    rows_html = ""
    for week in weeks:
        rows_html += "<tr>"
        for i, day in enumerate(week):
            if day == 0:
                rows_html += '<td style="background:#fafafa;border:1px solid #e8e8e8;padding:8px"></td>'
                continue
            d_str   = date(y, m, day).isoformat()
            is_vdag = i in VAGTDAG_IDX
            is_mine = d_str in my_shifts

            if is_vdag:
                if is_mine:
                    bg = "#1565c0"; num_color = "#fff"; badge = "Vagt"
                else:
                    bg = "#e3f2fd"; num_color = "#555"; badge = ""
                rows_html += (
                    f'<td style="background:{bg};border:1px solid #90caf9;'
                    f'padding:10px 4px;text-align:center;vertical-align:middle">'
                    f'<div style="font-size:18px;font-weight:700;color:{num_color}">{day}</div>'
                    + (f'<div style="font-size:11px;color:#fff;margin-top:3px">&#10003; {badge}</div>'
                       if is_mine else "")
                    + "</td>"
                )
            else:
                rows_html += (
                    f'<td style="background:#fafafa;border:1px solid #e8e8e8;'
                    f'padding:10px 4px;text-align:center;color:#ccc">'
                    f'<div style="font-size:14px">{day}</div></td>'
                )
        rows_html += "</tr>"

    return (
        '<div style="overflow-x:auto">'
        '<table style="border-collapse:collapse;width:100%;table-layout:fixed">'
        + _cal_header_html("#1565c0", "#bbb", "#1565c0")
        + f"<tbody>{rows_html}</tbody></table></div>"
    )

# ── Interaktiv praeferencekalender (frivillig) ────────────────────────────────
def render_pref_calendar(mkey: str, released_dates: set, existing: dict) -> dict:
    y, m   = int(mkey[:4]), int(mkey[5:7])
    weeks  = calendar.monthcalendar(y, m)
    prefs  = dict(existing)
    labels = ["Man","Tirs","Ons","Tor","Fre","Lor","Son"]

    hcols = st.columns(7)
    for i, name in enumerate(labels):
        is_vd = i in VAGTDAG_IDX
        hcols[i].markdown(
            f'<div style="text-align:center;font-weight:600;padding-bottom:4px;'
            f'border-bottom:3px solid {"#1565c0" if is_vd else "#e0e0e0"};'
            f'color:{"#1565c0" if is_vd else "#bbb"}">{name}</div>',
            unsafe_allow_html=True,
        )

    for week in weeks:
        wcols = st.columns(7)
        for i, day in enumerate(week):
            with wcols[i]:
                if day == 0:
                    st.markdown("&nbsp;", unsafe_allow_html=True)
                    continue
                d_str   = date(y, m, day).isoformat()
                is_vdag = i in VAGTDAG_IDX
                is_rel  = d_str in released_dates

                if is_vdag and is_rel:
                    current   = prefs.get(d_str, "")
                    day_color = "#1565c0" if current == "sikker" else "#e65100" if current == "maske" else "#555"
                    st.markdown(
                        f'<div style="text-align:center;font-size:16px;font-weight:700;'
                        f'color:{day_color};margin-bottom:2px">{day}</div>',
                        unsafe_allow_html=True,
                    )
                    lbl_map = {"":"—","sikker":"Ja","maske":"Maske"}
                    cur_lbl = lbl_map.get(current, "—")
                    sel = st.selectbox(
                        label=d_str,
                        options=["—","Ja","Maske"],
                        index=["—","Ja","Maske"].index(cur_lbl),
                        key=f"vo_{mkey}_{d_str}",
                        label_visibility="collapsed",
                    )
                    prefs[d_str] = {"—":"","Ja":"sikker","Maske":"maske"}[sel]
                else:
                    col = "#ddd" if not is_vdag else "#ccc"
                    st.markdown(
                        f'<div style="text-align:center;color:{col};'
                        f'font-size:14px;padding:6px 0">{day}</div>',
                        unsafe_allow_html=True,
                    )
    return prefs

# ── Interaktiv admin-kalender (opstaetning) ───────────────────────────────────
def render_setup_calendar(mkey: str, current_set: set) -> list:
    y, m   = int(mkey[:4]), int(mkey[5:7])
    weeks  = calendar.monthcalendar(y, m)
    labels = ["Man","Tirs","Ons","Tor","Fre","Lor","Son"]
    selected = []

    hcols = st.columns(7)
    for i, name in enumerate(labels):
        is_vd = i in VAGTDAG_IDX
        hcols[i].markdown(
            f'<div style="text-align:center;font-weight:600;padding-bottom:4px;'
            f'border-bottom:3px solid {"#2e7d32" if is_vd else "#e0e0e0"};'
            f'color:{"#2e7d32" if is_vd else "#bbb"}">{name}</div>',
            unsafe_allow_html=True,
        )

    for week in weeks:
        wcols = st.columns(7)
        for i, day in enumerate(week):
            with wcols[i]:
                if day == 0:
                    st.markdown("&nbsp;", unsafe_allow_html=True)
                    continue
                d_str   = date(y, m, day).isoformat()
                is_vdag = i in VAGTDAG_IDX
                if is_vdag:
                    checked = st.checkbox(str(day), value=d_str in current_set,
                                          key=f"dc_{mkey}_{d_str}")
                    if checked:
                        selected.append(d_str)
                else:
                    st.markdown(
                        f'<div style="text-align:center;color:#ccc;'
                        f'font-size:14px;padding:8px 0">{day}</div>',
                        unsafe_allow_html=True,
                    )
    return sorted(selected)

# ══════════════════════════════════════════════════════════════════════════════
#  FRIVILLIG-SIDE
# ══════════════════════════════════════════════════════════════════════════════
def side_frivillig(data: dict):
    if "vol_id" not in st.session_state:
        st.session_state.vol_id = None

    active_vols = {vid: v for vid, v in data["volunteers"].items() if v.get("active", True)}

    if st.session_state.vol_id is None:
        st.markdown("## Plexus Vagtplan")
        st.markdown("### Hvem er du?")
        if not active_vols:
            st.info("Ingen frivillige er oprettet endnu. Kontakt administratoren.")
            return
        navne = {v["name"]: vid for vid, v in sorted(active_vols.items(), key=lambda x: x[1]["name"])}
        valgt = st.selectbox("Vaelg dit navn", ["— Vaelg —"] + list(navne.keys()))
        if valgt != "— Vaelg —":
            st.session_state.vol_id = navne[valgt]
            st.rerun()
        return

    vid = st.session_state.vol_id
    if vid not in data["volunteers"]:
        st.session_state.vol_id = None
        st.rerun()

    vol = data["volunteers"][vid]

    c1, c2 = st.columns([5, 1])
    c1.markdown(f"## Hej, {vol['name']}!")
    if c2.button("<- Skift person"):
        st.session_state.vol_id = None
        st.rerun()
    st.divider()

    t1, t2 = st.tabs(["Vagtplan", "Vagtonsker"])
    with t1:
        _vol_vagtplan(data, vid, vol)
    with t2:
        _vol_vagtonsker(data, vid, vol)


def _vol_vagtplan(data: dict, vid: str, vol: dict):
    assignments = data.get("assignments", {})
    released    = [k for k, c in data["monthly_config"].items() if c.get("released")]
    all_months  = sorted(set(list(assignments.keys()) + released), reverse=True)

    if not all_months:
        st.info("Ingen vagtplaner er tilgaengelige endnu.")
        return

    now      = datetime.now()
    cur_mk   = mk(now.year, now.month)
    default  = cur_mk if cur_mk in all_months else all_months[0]
    sel_mk   = st.selectbox("Maaned", all_months, index=all_months.index(default),
                             format_func=mk_label, key="vp_month")

    if sel_mk not in assignments:
        st.info(f"Vagtplanen for **{mk_label(sel_mk)}** er endnu ikke genereret. "
                "Tjek igen, naar administratoren har tildelt vagterne.")
        return

    asgn      = assignments[sel_mk]
    my_shifts = sorted(d for d, vs in asgn["shifts"].items() if vid in vs)
    kraevet   = vol.get("required_shifts", 2)

    st.markdown(f"**{mk_label(sel_mk)}** — du har **{len(my_shifts)}/{kraevet}** vagter")
    if len(my_shifts) < kraevet:
        st.warning(f"Du fik {kraevet - len(my_shifts)} faerre vagt(er) end aftalt.")

    st.markdown(cal_html_vagtplan(sel_mk, my_shifts), unsafe_allow_html=True)
    st.markdown("")

    if my_shifts:
        st.markdown("**Dine vagter:**")
        for d in my_shifts:
            st.success(f"  {fmt(d)}")
    else:
        st.info("Du er ikke tildelt vagter denne maaned.")


def _vol_vagtonsker(data: dict, vid: str, vol: dict):
    frigivne    = sorted(k for k, c in data["monthly_config"].items() if c.get("released"))
    assignments = data.get("assignments", {})
    aabne       = [k for k in frigivne if k not in assignments]

    if not aabne:
        if frigivne:
            st.info("Vagtplanen er genereret for de frigivne maaneder. Se fanen **Vagtplan** for dine vagter.")
        else:
            st.info("Ingen maaneder er frigivet endnu. Tjek igen senere.")
        return

    sel_mk   = st.selectbox("Maaned", aabne, format_func=mk_label, key="vo_month")
    cfg      = data["monthly_config"][sel_mk]
    rel_set  = set(cfg.get("dates", []))
    min_sel  = cfg.get("min_selections", 5)
    existing = data["preferences"].get(sel_mk, {}).get(vid, {})

    st.markdown(f"**{mk_label(sel_mk)}** — vaelg mindst **{min_sel}** datoer")
    st.caption(f"Din aftalte kvote denne maaned: **{vol.get('required_shifts', 2)} vagter**")

    pkey = f"prefs_{sel_mk}_{vid}"
    if pkey not in st.session_state:
        st.session_state[pkey] = dict(existing)

    prefs = render_pref_calendar(sel_mk, rel_set, st.session_state[pkey])
    st.session_state[pkey] = prefs

    markeret = sum(1 for p in prefs.values() if p)
    nok      = markeret >= min_sel

    st.divider()
    ci, cb = st.columns([4, 1])
    ci.markdown(
        ("**" + str(markeret) + "** datoer valgt — "
         + ("klar til at gemme" if nok else f"vaelg {min_sel - markeret} mere"))
    )
    if cb.button("Gem onsker", type="primary", disabled=not nok):
        if sel_mk not in data["preferences"]:
            data["preferences"][sel_mk] = {}
        data["preferences"][sel_mk][vid] = {k: v for k, v in prefs.items() if v}
        save(data)
        st.success("Dine onsker er gemt! Du kan aendre dem igen naar som helst inden planen genereres.")

# ══════════════════════════════════════════════════════════════════════════════
#  ADMIN-SIDE
# ══════════════════════════════════════════════════════════════════════════════
def side_admin(data: dict):
    if "admin_ok" not in st.session_state:
        st.session_state.admin_ok = False

    if not st.session_state.admin_ok:
        st.header("Administratorlogin")
        pwd = st.text_input("Adgangskode", type="password")
        if st.button("Log ind", type="primary"):
            if pwd == data.get("admin_password", "plexus2024"):
                st.session_state.admin_ok = True
                st.rerun()
            else:
                st.error("Forkert adgangskode.")
        return

    c1, c2 = st.columns([5, 1])
    c1.header("Administration")
    if c2.button("Log ud"):
        st.session_state.admin_ok = False
        st.rerun()

    t1, t2, t3, t4 = st.tabs(
        ["Frivillige", "Maaneds-opstaetning", "Vagttildeling", "Resultater"]
    )
    with t1: _tab_frivillige(data)
    with t2: _tab_setup(data)
    with t3: _tab_tildeling(data)
    with t4: _tab_resultater(data)


def _tab_frivillige(data: dict):
    st.subheader("Frivillige")

    with st.expander("Tilfoj ny frivillig", expanded=not data["volunteers"]):
        with st.form("add_vol", clear_on_submit=True):
            c1, c2 = st.columns(2)
            navn  = c1.text_input("Navn")
            kvote = c2.number_input("Vagter/maaned", 1, 20, 2)
            if st.form_submit_button("Tilfoj frivillig"):
                if navn.strip():
                    nid = str(data.get("next_id", 1))
                    data["volunteers"][nid] = {
                        "name": navn.strip(),
                        "required_shifts": int(kvote),
                        "active": True,
                    }
                    data["next_id"] = int(nid) + 1
                    save(data)
                    st.success(f"{navn.strip()} tilfojet!")
                    st.rerun()
                else:
                    st.warning("Angiv et navn.")

    if not data["volunteers"]:
        st.info("Ingen frivillige oprettet endnu.")
        return

    h1, h2, h3, h4 = st.columns([3, 2, 1, 1])
    h1.markdown("**Navn**"); h2.markdown("**Vagter/md.**"); h3.markdown("**Aktiv**")
    st.divider()

    edits = {}
    for vid, vol in sorted(data["volunteers"].items(), key=lambda x: x[1]["name"]):
        c1, c2, c3, c4 = st.columns([3, 2, 1, 1])
        c1.write(vol["name"])
        q = c2.number_input("", 1, 20, vol.get("required_shifts", 2),
                             key=f"q_{vid}", label_visibility="collapsed")
        a = c3.checkbox("", vol.get("active", True),
                        key=f"a_{vid}", label_visibility="collapsed")
        edits[vid] = {"required_shifts": int(q), "active": a}
        if c4.button("Slet", key=f"del_{vid}"):
            del data["volunteers"][vid]
            save(data)
            st.rerun()

    st.divider()
    if st.button("Gem alle aendringer", type="primary"):
        for vid, vals in edits.items():
            if vid in data["volunteers"]:
                data["volunteers"][vid].update(vals)
        save(data)
        st.success("Alle aendringer gemt!")

    with st.expander("Skift admin-adgangskode"):
        with st.form("pwd_form"):
            p1 = st.text_input("Ny adgangskode", type="password")
            p2 = st.text_input("Gentag ny adgangskode", type="password")
            if st.form_submit_button("Gem adgangskode"):
                if p1 and p1 == p2:
                    data["admin_password"] = p1
                    save(data)
                    st.success("Adgangskode aendret.")
                else:
                    st.error("Adgangskoderne matcher ikke.")


def _tab_setup(data: dict):
    st.subheader("Maaneds-opstaetning")

    now = datetime.now()
    c1, c2 = st.columns(2)
    ar  = int(c1.number_input("Ar", 2024, 2030, now.year))
    mdr = int(c2.selectbox("Maaned", range(1, 13), index=now.month - 1,
                             format_func=lambda x: MANEDER[x]))

    mkey   = mk(ar, mdr)
    cfg    = data["monthly_config"].get(mkey, {})
    locked = cfg.get("released", False)

    if locked:
        st.success(
            f"**{MANEDER[mdr]} {ar}** er frigivet og laast. "
            "Opstaetningen kan ikke aendres."
        )
        st.markdown(
            f"- **Vagtdatoer:** {len(cfg.get('dates', []))} datoer  \n"
            f"- **Min. frivillige/vagt:** {cfg.get('min_per_shift', 1)}  \n"
            f"- **Max. frivillige/vagt:** {cfg.get('max_per_shift', 5)}  \n"
            f"- **Min. onsker/frivillig:** {cfg.get('min_selections', 5)}"
        )
        prefs_m = data["preferences"].get(mkey, {})
        aktive  = sum(1 for v in data["volunteers"].values() if v.get("active", True))
        st.info(f"{len(prefs_m)}/{aktive} aktive frivillige har indsendt onsker.")
        return

    alle        = all_vagtdates(ar, mdr)
    current_set = set(cfg.get("dates", alle))

    st.markdown("**Vaelg aktive vagtdatoer** (Man/Tirs/Ons/Son er aktive som standard):")
    selected = render_setup_calendar(mkey, current_set)

    st.divider()
    c3, c4, c5 = st.columns(3)
    min_per = c3.number_input("Min. frivillige/vagt", 1, 10, cfg.get("min_per_shift", 1))
    max_per = c4.number_input("Max. frivillige/vagt", 1, 20, cfg.get("max_per_shift", 5))
    min_sel = c5.number_input("Min. onsker/frivillig", 1, 20, cfg.get("min_selections", 5))

    cs, cr = st.columns(2)
    if cs.button("Gem opstaetning (ikke frigivet endnu)", use_container_width=True):
        data["monthly_config"][mkey] = {
            "dates": selected,
            "min_per_shift": int(min_per),
            "max_per_shift": int(max_per),
            "min_selections": int(min_sel),
            "released": False,
        }
        save(data)
        st.success(f"Opstaetning for {MANEDER[mdr]} {ar} gemt.")

    if cr.button("Frigiv til frivillige", type="primary", use_container_width=True):
        if not selected:
            st.error("Vaelg mindst een dato inden du frigiver.")
        else:
            data["monthly_config"][mkey] = {
                "dates": selected,
                "min_per_shift": int(min_per),
                "max_per_shift": int(max_per),
                "min_selections": int(min_sel),
                "released": True,
            }
            save(data)
            st.success(f"{MANEDER[mdr]} {ar} er nu frigivet til de frivillige!")
            st.rerun()

    prefs_m = data["preferences"].get(mkey, {})
    aktive  = sum(1 for v in data["volunteers"].values() if v.get("active", True))
    if aktive:
        st.info(f"{len(prefs_m)}/{aktive} aktive frivillige har indsendt onsker.")


def _tab_tildeling(data: dict):
    st.subheader("Automatisk vagttildeling")

    frigivne = sorted(k for k, c in data["monthly_config"].items() if c.get("released"))
    if not frigivne:
        st.warning("Ingen maaneder er frigivet endnu.")
        return

    mkey    = st.selectbox("Vaelg maaned", frigivne, format_func=mk_label)
    prefs_m = data["preferences"].get(mkey, {})
    aktive  = {vid: v for vid, v in data["volunteers"].items() if v.get("active", True)}

    c1, c2 = st.columns(2)
    c1.metric("Har indsendt onsker", f"{len(prefs_m)}/{len(aktive)}")

    col_ja, col_nej = st.columns(2)
    with col_ja:
        st.markdown("**Klar:**")
        for vid, v in aktive.items():
            if vid in prefs_m:
                s  = sum(1 for p in prefs_m[vid].values() if p == "sikker")
                ms = sum(1 for p in prefs_m[vid].values() if p == "maske")
                st.write(f"- {v['name']}  (Ja: {s} / Maske: {ms})")
    with col_nej:
        st.markdown("**Mangler:**")
        for vid, v in aktive.items():
            if vid not in prefs_m:
                st.write(f"- {v['name']}")

    st.divider()
    if mkey in data.get("assignments", {}):
        st.warning("Vagter er allerede tildelt — klik nedenfor for at kore forfra.")

    if st.button("Tildel vagter automatisk", type="primary"):
        if not prefs_m:
            st.error("Ingen frivillige har indsendt onsker endnu.")
        else:
            data = auto_assign(data, mkey)
            save(data)
            st.success("Vagter er tildelt!")
            st.rerun()


def _tab_resultater(data: dict):
    st.subheader("Resultater")

    tildelte = sorted(data.get("assignments", {}).keys(), reverse=True)
    if not tildelte:
        st.info("Ingen vagter er tildelt endnu.")
        return

    mkey = st.selectbox("Vaelg maaned", tildelte, format_func=mk_label)
    asgn = data["assignments"][mkey]
    vols = data["volunteers"]

    st.caption(f"Genereret: {asgn.get('generated_at', '–')}")

    aabne   = len(asgn["open"])
    lukkede = len(asgn["closed"])
    total   = aabne + lukkede
    pct     = round(100 * aabne / total) if total > 0 else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("Aabningsdage",    aabne)
    c2.metric("Lukkedage",       lukkede)
    c3.metric("Aabningsprocent", f"{pct}%")

    if asgn.get("unmet_quota"):
        with st.expander("Frivillige med ufyldt kvote"):
            for vid, mangler in asgn["unmet_quota"].items():
                st.write(f"- **{vols.get(vid, {}).get('name', vid)}** mangler {mangler} vagt(er)")

    st.markdown("### Kalender-oversigt")
    st.markdown(cal_html_results(mkey, asgn["shifts"], asgn["open"], vols), unsafe_allow_html=True)

    with st.expander("Oversigt per frivillig"):
        for vid, vol in sorted(vols.items(), key=lambda x: x[1]["name"]):
            if not vol.get("active"):
                continue
            mine   = sorted(d for d, vs in asgn["shifts"].items() if vid in vs)
            kraevet = vol.get("required_shifts", 2)
            st.markdown(f"**{vol['name']}** — {len(mine)}/{kraevet} vagter")
            for d in mine:
                st.write(f"  - {fmt(d)}")

    rakker = ["Dato,Status,Frivillige"]
    for d in sorted(asgn["shifts"]):
        navne  = "; ".join(vols[v]["name"] for v in asgn["shifts"][d] if v in vols)
        status = "Aben" if d in asgn["open"] else "Lukket"
        rakker.append(f"{fmt(d)},{status},{navne}")

    st.download_button(
        "Download CSV",
        "\n".join(rakker).encode("utf-8-sig"),
        f"plexus_vagtplan_{mkey}.csv",
        "text/csv",
    )

# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    st.set_page_config(page_title="Plexus Vagtplan", page_icon="", layout="wide")
    st.markdown(
        """
        <style>
        .block-container { padding-top: 1.8rem; }
        div[data-testid="stMetric"] {
            background: #f0f4f8; border-radius: 8px; padding: 12px 16px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    data = load()

    with st.sidebar:
        st.markdown("## Plexus Vagtplan")
        st.divider()
        side = st.radio("", ["Frivillig", "Administrator"], label_visibility="hidden")
        st.divider()
        st.caption(f"Version {VERSION}")
        st.caption("Lavet af Fabian Salvatore")

    if side == "Frivillig":
        side_frivillig(data)
    else:
        side_admin(data)


if __name__ == "__main__":
    main()

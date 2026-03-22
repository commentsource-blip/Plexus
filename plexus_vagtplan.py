# -*- coding: utf-8 -*-
"""
Plexus Vagtplan
Lavet af Fabian Salvatore
"""
import streamlit as st
import json, os, calendar
from datetime import date, datetime
from io import StringIO

# ── Konstanter ────────────────────────────────────────────────────────────────
VERSION     = date.today().strftime("%d.%m.%Y")
DATA_FILE   = "plexus_data.json"
VAGTDAG_IDX = {0, 1, 2, 6}

DAG_KORT = {0:"Man", 1:"Tirs", 2:"Ons", 3:"Tor", 4:"Fre", 5:"Lør", 6:"Søn"}
DAG_LANG = {0:"Mandag", 1:"Tirsdag", 2:"Onsdag", 3:"Torsdag",
            4:"Fredag",  5:"Lørdag",  6:"Søndag"}
MÅNEDER     = ["","Januar","Februar","Marts","April","Maj","Juni",
               "Juli","August","September","Oktober","November","December"]
MÅNEDER_GEN = ["","januar","februar","marts","april","maj","juni",
               "juli","august","september","oktober","november","december"]

OPEN = "open"; CLOSED = "closed"; ACTIVITY = "activity"

SETUP_CYCLE = {OPEN: CLOSED, CLOSED: ACTIVITY, ACTIVITY: OPEN}
SETUP_STYLE = {
    OPEN:     ("#c8e6c9","#4caf50","#1b5e20","🟢","Åben"),
    CLOSED:   ("#ffebee","#ef5350","#b71c1c","🔴","Lukket"),
    ACTIVITY: ("#dbeafe","#1d4ed8","#1e3a8a","🔵","Aktivitet"),
}
PREF_CYCLE  = {"":"sikker","sikker":"måske","måske":""}
PREF_STYLE  = {
    "":       ("#f8f9fa","#dee2e6","#adb5bd","⬜","—"),
    "sikker": ("#c8e6c9","#4caf50","#1b5e20","✅","Ja"),
    "måske":  ("#fff9c4","#f59e0b","#92400e","🟡","Måske"),
}

# ── CSS ────────────────────────────────────────────────────────────────────────
CSS = """
<style>
.block-container{padding-top:1.2rem !important}
div[data-testid="stMetric"]{
  background:linear-gradient(135deg,#f0f9ff,#e8f5e9);
  border-radius:12px;padding:14px 18px;border:1px solid #e0e0e0}
div[data-testid="stMetric"] label{font-size:12px !important;color:#607d8b !important}
div[data-testid="stMetric"] [data-testid="stMetricValue"]{font-size:28px !important;font-weight:800 !important}
div[data-testid="stTabs"] button[data-baseweb="tab"]{font-size:14px;font-weight:600;padding:8px 18px}
.stButton>button{border-radius:10px !important;font-weight:500 !important}
.stButton>button[kind="primary"]{background:linear-gradient(135deg,#1565c0,#0d47a1) !important;
  border:none !important;color:white !important}
/* mobile warning */
.mobile-warn{display:none}
@media(max-width:720px){.mobile-warn{display:block !important}}
@media(max-width:720px){.admin-content{display:none !important}}
</style>
"""

# ── Data-hjælpere ──────────────────────────────────────────────────────────────
def load() -> dict:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE,"r",encoding="utf-8") as f:
            return json.load(f)
    return {"volunteers":{},"monthly_config":{},"preferences":{},
            "assignments":{},"admin_password":"plexus2024","next_id":1}

def save(data:dict):
    with open(DATA_FILE,"w",encoding="utf-8") as f:
        json.dump(data,f,ensure_ascii=False,indent=2)

def mk(y,m)->str: return f"{y}-{m:02d}"
def mk_label(k)->str:
    y,m=k.split("-"); return f"{MÅNEDER[int(m)]} {y}"
def full_date_str(d_str:str)->str:
    d=date.fromisoformat(d_str)
    return f"{DAG_LANG[d.weekday()]} den {d.day}. {MÅNEDER_GEN[d.month]}"

def default_date_types(y:int,m:int)->dict:
    n=calendar.monthrange(y,m)[1]
    return {date(y,m,d).isoformat(): (OPEN if date(y,m,d).weekday() in VAGTDAG_IDX else CLOSED)
            for d in range(1,n+1)}

def cfg_date_types(cfg:dict,y:int,m:int)->dict:
    if "date_types" in cfg:
        return cfg["date_types"]
    dates=cfg.get("dates",[])
    return {d:OPEN for d in dates}

def next_plan_month(data:dict)->tuple:
    assigned=sorted(data.get("assignments",{}).keys())
    if assigned:
        y,m=int(assigned[-1][:4]),int(assigned[-1][5:7])
    else:
        now=datetime.now(); y,m=now.year,now.month
    return (y+1,1) if m==12 else (y,m+1)

# ── Fordelingsalgoritme ────────────────────────────────────────────────────────
def auto_assign(data:dict,mkey:str)->dict:
    cfg        = data["monthly_config"].get(mkey,{})
    y,m        = int(mkey[:4]),int(mkey[5:7])
    dt         = cfg_date_types(cfg,y,m)
    active_dates= [d for d,t in dt.items() if t in (OPEN,ACTIVITY)]
    min_per    = cfg.get("min_per_shift",3)
    max_per    = cfg.get("max_per_shift",6)
    prefs_m    = data["preferences"].get(mkey,{})
    vols       = data["volunteers"]
    active     = [vid for vid,v in vols.items() if v.get("active",True)]
    is_aktiv   = {vid:vols[vid].get("aktivitetsudvalg",False) for vid in active}

    prio = {vid:{d:(2 if prefs_m.get(vid,{}).get(d)=="sikker"
                    else 1 if prefs_m.get(vid,{}).get(d)=="måske" else 0)
                 for d in active_dates}
            for vid in active}

    remaining  = {vid:vols[vid].get("required_shifts",2) for vid in active}
    shifts     = {d:[] for d in active_dates}

    def priority_groups(d):
        if dt.get(d)==ACTIVITY:
            return [
                [v for v in active if is_aktiv[v]     and prio[v][d]==2],
                [v for v in active if is_aktiv[v]     and prio[v][d]==1],
                [v for v in active if not is_aktiv[v] and prio[v][d]==2],
                [v for v in active if not is_aktiv[v] and prio[v][d]==1],
            ]
        return [
            [v for v in active if prio[v][d]==2],
            [v for v in active if prio[v][d]==1],
        ]

    sorted_dates=sorted(active_dates,key=lambda d:sum(1 for v in active if prio[v][d]>0))

    # Fase 1: opnå min_per_shift
    for d in sorted_dates:
        if len(shifts[d])>=min_per: continue
        for grp in priority_groups(d):
            cands=[v for v in grp if remaining[v]>0 and v not in shifts[d] and len(shifts[d])<max_per]
            cands.sort(key=lambda v:remaining[v],reverse=True)
            for v in cands:
                if len(shifts[d])>=min_per: break
                shifts[d].append(v); remaining[v]-=1

    # Fase 2: fyld resterende kvote
    for vid in sorted(active,key=lambda v:remaining[v],reverse=True):
        while remaining[vid]>0:
            cands=[d for d in active_dates
                   if prio[vid][d]>0 and vid not in shifts[d] and len(shifts[d])<max_per]
            if not cands: break
            cands.sort(key=lambda d:(len(shifts[d])>=min_per,-prio[vid][d],len(shifts[d])))
            shifts[cands[0]].append(vid); remaining[vid]-=1

    open_d    =[d for d in active_dates if len(shifts[d])>=min_per]
    closed_d  =[d for d in active_dates if len(shifts[d])<min_per]+[d for d,t in dt.items() if t==CLOSED]
    activity_d=[d for d in active_dates if dt.get(d)==ACTIVITY]

    data["assignments"][mkey]={
        "shifts":shifts,"open":open_d,"closed":closed_d,"activity":activity_d,
        "unmet_quota":{v:remaining[v] for v in active if remaining[v]>0},
        "generated_at":datetime.now().strftime("%d/%m/%Y %H:%M"),
    }
    return data

# ══════════════════════════════════════════════════════════════════════════════
#  KALENDER: statisk HTML (resultater + frivillig vagtplan)
# ══════════════════════════════════════════════════════════════════════════════
def _html_header()->str:
    cells=""
    for i in range(7):
        is_vd=i in VAGTDAG_IDX
        cells+=(f'<th style="padding:10px 6px;font-size:12px;font-weight:700;'
                f'letter-spacing:0.5px;border:1px solid #e0e0e0;'
                f'background:{"#f0f7ff" if is_vd else "#f9f9f9"};'
                f'color:{"#1565c0" if is_vd else "#bbb"};'
                f'border-bottom:3px solid {"#1565c0" if is_vd else "#e0e0e0"}">'
                f'{DAG_LANG[i]}</th>')
    return f"<thead><tr>{cells}</tr></thead>"

def cal_static_resultater(mkey:str,shifts:dict,open_days:list,closed_days:list,
                           activity_days:list,vols:dict,highlight_vid:str=None)->str:
    y,m=int(mkey[:4]),int(mkey[5:7])
    rows=""
    for week in calendar.monthcalendar(y,m):
        rows+="<tr>"
        for i,day in enumerate(week):
            if day==0:
                rows+='<td style="background:#fafafa;border:1px solid #ececec;padding:6px"></td>'
                continue
            d_str=date(y,m,day).isoformat()
            is_vdag=i in VAGTDAG_IDX
            if is_vdag:
                is_open=d_str in open_days
                is_act =d_str in activity_days
                navne  =[vols[v]["name"] for v in shifts.get(d_str,[]) if v in vols]
                if is_act and is_open:
                    bg,hdr,dot,label="#dbeafe","#1e3a8a","🔵","Aktivitet"
                elif is_open:
                    bg,hdr,dot,label="#e8f5e9","#1b5e20","🟢","Åben"
                else:
                    bg,hdr,dot,label="#ffebee","#b71c1c","🔴","Lukket"

                names_html=""
                for v_id,name in [(v,vols[v]["name"]) for v in shifts.get(d_str,[]) if v in vols]:
                    mine=v_id==highlight_vid
                    names_html+=(f'<div style="font-size:11px;margin-top:2px;padding:1px 6px;'
                                 f'border-radius:4px;'
                                 f'background:{"#c8e6c9" if mine else "#ffffffcc"};'
                                 f'color:{"#1b5e20" if mine else "#333"};'
                                 f'font-weight:{"700" if mine else "400"}">'
                                 f'{"★ " if mine else ""}{name}</div>')
                rows+=(f'<td style="background:{bg};border:1px solid #ccc;'
                       f'padding:8px 5px;vertical-align:top;min-width:90px">'
                       f'<div style="font-size:10px;font-weight:700;color:{hdr}">'
                       f'{DAG_KORT[i]}</div>'
                       f'<div style="font-size:20px;font-weight:900;color:{hdr};line-height:1">{day}</div>'
                       f'<div style="font-size:9px;color:{hdr};margin-bottom:3px">'
                       f'{MÅNEDER_GEN[m]}</div>'
                       f'<div style="font-size:10px;color:{hdr}">{dot} {label}</div>'
                       f'{names_html}</td>')
            else:
                rows+=(f'<td style="background:#fafafa;border:1px solid #ececec;'
                       f'padding:8px 4px;text-align:center;color:#ccc;vertical-align:top">'
                       f'<div style="font-size:12px">{day}</div></td>')
        rows+="</tr>"
    return (f'<div style="overflow-x:auto;border-radius:12px;'
            f'border:1px solid #e0e0e0;overflow:hidden">'
            f'<table style="border-collapse:collapse;width:100%;table-layout:fixed">'
            +_html_header()+f"<tbody>{rows}</tbody></table></div>")

# ══════════════════════════════════════════════════════════════════════════════
#  KALENDER: interaktiv med klikbare celler (Streamlit)
# ══════════════════════════════════════════════════════════════════════════════
def _cal_dag_header(border_color:str,text_color:str):
    cols=st.columns(7)
    for i in range(7):
        is_vd=i in VAGTDAG_IDX
        cols[i].markdown(
            f'<div style="text-align:center;font-size:11px;font-weight:700;'
            f'padding:6px 0;letter-spacing:0.5px;text-transform:uppercase;'
            f'border-bottom:3px solid {"" if not is_vd else border_color};'
            f'color:{text_color if is_vd else "#ccc"}">'
            f'{DAG_LANG[i][:3] if is_vd else DAG_LANG[i][:3]}</div>',
            unsafe_allow_html=True)

def _cell(bg,border,text,dag_kort,day,maaned_kort,status_txt,btn_label,key)->bool:
    st.markdown(
        f'<div style="background:{bg};border:2px solid {border};'
        f'border-radius:10px 10px 0 0;padding:8px 4px 6px;text-align:center;'
        f'min-height:84px;display:flex;flex-direction:column;align-items:center;'
        f'justify-content:space-between;cursor:pointer">'
        f'<div style="font-size:9px;font-weight:700;color:{text};'
        f'text-transform:uppercase;letter-spacing:0.4px">{dag_kort}</div>'
        f'<div style="font-size:24px;font-weight:900;color:{text};line-height:1.1">{day}</div>'
        f'<div style="font-size:9px;color:{text};opacity:0.75">{maaned_kort}</div>'
        f'<div style="font-size:11px;font-weight:600;color:{text};margin-top:2px">{status_txt}</div>'
        f'</div>',
        unsafe_allow_html=True)
    return st.button(btn_label,key=key,use_container_width=True)

def _empty_cell(day:int,is_vdag:bool):
    if is_vdag:
        st.markdown(
            f'<div style="background:#f5f5f5;border:1px solid #eee;border-radius:10px;'
            f'padding:8px 4px;text-align:center;min-height:84px;'
            f'display:flex;align-items:center;justify-content:center;color:#ccc">'
            f'<div style="font-size:18px">{day}</div></div>',
            unsafe_allow_html=True)
    else:
        st.markdown(
            f'<div style="text-align:center;color:#e0e0e0;'
            f'font-size:14px;padding:18px 0">{day if day else ""}</div>',
            unsafe_allow_html=True)

# ── Setup-kalender (3 tilstande: open/closed/activity) ────────────────────────
def render_setup_kalender(mkey:str)->dict:
    y,m=int(mkey[:4]),int(mkey[5:7])
    sk=f"sc_{mkey}"
    if sk not in st.session_state:
        st.session_state[sk]=default_date_types(y,m)

    _cal_dag_header("#2e7d32","#2e7d32")

    for week in calendar.monthcalendar(y,m):
        cols=st.columns(7)
        for i,day in enumerate(week):
            with cols[i]:
                if day==0:
                    st.markdown('<div style="height:110px"></div>',unsafe_allow_html=True)
                    continue
                d_str=date(y,m,day).isoformat()
                state=st.session_state[sk].get(d_str,CLOSED)
                bg,border,text,icon,label=SETUP_STYLE[state]
                next_s=SETUP_CYCLE[state]
                _,_,_,next_icon,next_label=SETUP_STYLE[next_s]
                if _cell(bg,border,text,DAG_LANG[i][:3],day,
                         MÅNEDER_GEN[m][:3],f"{icon} {label}",
                         f"→ {next_icon} {next_label}",f"sc_{mkey}_{d_str}"):
                    st.session_state[sk][d_str]=next_s
                    st.rerun()
    return dict(st.session_state[sk])

# ── Præference-kalender (3 tilstande: /sikker/måske) ──────────────────────────
def render_pref_kalender(mkey:str,vid:str,released_set:set,existing:dict,
                          mobile:bool=False)->dict:
    y,m=int(mkey[:4]),int(mkey[5:7])
    sk=f"vp_{mkey}_{vid}"
    if sk not in st.session_state:
        st.session_state[sk]=dict(existing)

    n_cols=3 if mobile else 7
    if mobile:
        # Mobilvisning: 3 kolonner, stør celler
        dag_labels=[DAG_LANG[i] for i in range(7)]
        hcols=st.columns(3)
        for ci,(label,color) in enumerate([("✅ Grøn = Ja","#1b5e20"),
                                           ("🟡 Gul = Måske","#7c6000"),
                                           ("⬜ = Ikke valgt","#888")]):
            hcols[ci].markdown(
                f'<div style="text-align:center;font-size:11px;font-weight:600;'
                f'color:{color};padding:4px 0">{label}</div>',unsafe_allow_html=True)

        all_dates=sorted(released_set)
        for i in range(0,len(all_dates),3):
            batch=all_dates[i:i+3]
            cols=st.columns(3)
            for ci,d_str in enumerate(batch):
                with cols[ci]:
                    d=date.fromisoformat(d_str)
                    state=st.session_state[sk].get(d_str,"")
                    bg,border,text,icon,label=PREF_STYLE[state]
                    next_s=PREF_CYCLE[state]
                    _,_,_,next_icon,next_label=PREF_STYLE[next_s]
                    full=f"{DAG_LANG[d.weekday()][:3]}\n{d.day}. {MÅNEDER_GEN[d.month][:3]}"
                    if _cell(bg,border,text,DAG_LANG[d.weekday()][:3],
                             d.day,MÅNEDER_GEN[d.month][:3],
                             f"{icon} {label}",f"→ {next_icon} {next_label}",
                             f"vp_{mkey}_{vid}_{d_str}"):
                        st.session_state[sk][d_str]=next_s
                        st.rerun()
    else:
        _cal_dag_header("#1565c0","#1565c0")
        for week in calendar.monthcalendar(y,m):
            cols=st.columns(7)
            for i,day in enumerate(week):
                with cols[i]:
                    if day==0:
                        st.markdown('<div style="height:110px"></div>',unsafe_allow_html=True)
                        continue
                    d_str=date(y,m,day).isoformat()
                    is_vdag=i in VAGTDAG_IDX
                    is_rel =d_str in released_set
                    if is_vdag and is_rel:
                        state=st.session_state[sk].get(d_str,"")
                        bg,border,text,icon,label=PREF_STYLE[state]
                        next_s=PREF_CYCLE[state]
                        _,_,_,next_icon,next_label=PREF_STYLE[next_s]
                        if _cell(bg,border,text,DAG_LANG[i][:3],day,
                                 MÅNEDER_GEN[m][:3],f"{icon} {label}",
                                 f"→ {next_icon} {next_label}",
                                 f"vp_{mkey}_{vid}_{d_str}"):
                            st.session_state[sk][d_str]=next_s
                            st.rerun()
                    else:
                        _empty_cell(day,is_vdag)

    return dict(st.session_state[sk])

# ══════════════════════════════════════════════════════════════════════════════
#  FRIVILLIG-SIDE
# ══════════════════════════════════════════════════════════════════════════════
def side_frivillig(data:dict):
    if "vol_id" not in st.session_state: st.session_state.vol_id=None

    active_vols={vid:v for vid,v in data["volunteers"].items() if v.get("active",True)}

    # ── Navnevalg ──────────────────────────────────────────────────────────────
    if st.session_state.vol_id is None:
        st.markdown("## 📅 Plexus Vagtplan")
        st.markdown("### 👋 Hvem er du?")
        st.caption("Vælg dit navn for at se din vagtplan eller indsende vagtønsker.")
        if not active_vols:
            st.info("Ingen frivillige er oprettet endnu. Kontakt administratoren.")
            return
        navne={v["name"]:vid for vid,v in sorted(active_vols.items(),key=lambda x:x[1]["name"])}
        valgt=st.selectbox("",["— Vælg dit navn —"]+list(navne.keys()),
                           label_visibility="collapsed")
        if valgt!="— Vælg dit navn —":
            st.session_state.vol_id=navne[valgt]
            st.rerun()
        return

    vid=st.session_state.vol_id
    if vid not in data["volunteers"]:
        st.session_state.vol_id=None; st.rerun()

    vol=data["volunteers"][vid]
    col_h,col_b=st.columns([5,1])
    col_h.markdown(f"## 👋 Hej, {vol['name']}!")
    col_b.markdown('<div style="margin-top:18px"></div>',unsafe_allow_html=True)
    if col_b.button("← Skift",use_container_width=True):
        st.session_state.vol_id=None; st.rerun()
    st.divider()

    # ── Månedsvælger ───────────────────────────────────────────────────────────
    released = {k for k,c in data["monthly_config"].items() if c.get("released")}
    assigned = set(data.get("assignments",{}).keys())
    alle     = sorted(released|assigned,reverse=True)

    if not alle:
        st.info("📭 Ingen måneder er tilgængelige endnu.")
        return

    sel_mk=st.selectbox("📅 Vælg periode",alle,index=0,format_func=mk_label)
    st.markdown("")

    if sel_mk in assigned:
        _vis_vagtplan(data,vid,vol,sel_mk)
    elif sel_mk in released:
        _vis_praeference(data,vid,vol,sel_mk)
    else:
        st.info("Denne måned er ikke frigivet endnu.")

def _vis_vagtplan(data:dict,vid:str,vol:dict,mkey:str):
    asgn     =data["assignments"][mkey]
    my_shifts=sorted(d for d,vs in asgn["shifts"].items() if vid in vs)
    kraevet  =vol.get("required_shifts",2)

    c1,c2,c3=st.columns(3)
    c1.metric("✅ Dine vagter",     f"{len(my_shifts)}/{kraevet}")
    c2.metric("🟢 Åbningsdage",     len(asgn["open"]))
    c3.metric("🔴 Lukkedage",       len(asgn["closed"]))

    st.markdown("### 📅 Vagtplan")
    st.markdown(
        cal_static_resultater(mkey,asgn["shifts"],asgn["open"],asgn["closed"],
                               asgn.get("activity",[]),data["volunteers"],highlight_vid=vid),
        unsafe_allow_html=True)

    if my_shifts:
        st.markdown("---")
        st.markdown("**🗓️ Dine vagter denne måned:**")
        for d in my_shifts:
            st.success(f"  ✅ {full_date_str(d)}")
    else:
        st.info("Du er ikke tildelt vagter denne måned.")
    if len(my_shifts)<kraevet:
        st.warning(f"⚠️ Du fik {kraevet-len(my_shifts)} færre vagt(er) end aftalt.")

def _vis_praeference(data:dict,vid:str,vol:dict,mkey:str):
    cfg     =data["monthly_config"][mkey]
    y,m     =int(mkey[:4]),int(mkey[5:7])
    dt      =cfg_date_types(cfg,y,m)
    rel_set =set(d for d,t in dt.items() if t in (OPEN,ACTIVITY))
    min_sel =cfg.get("min_selections",5)
    existing=data["preferences"].get(mkey,{}).get(vid,{})

    if data["preferences"].get(mkey,{}).get(vid):
        st.success("✅ Du har allerede gemt ønsker — du kan ændre dem nedenfor.")

    st.markdown(f"### ✏️ Vagtønsker – {mk_label(mkey)}")

    # Mobiltoggle
    mobile=st.toggle("📱 Mobilvenlig visning",key="mob_pref",value=False)
    if mobile:
        st.caption("3-kolonnet layout til mobilskærme")
    else:
        st.markdown(
            "**Klik på datoerne for at angive dine ønsker:**  \n"
            "✅ **Grøn = Ja** &nbsp;&nbsp;&nbsp; 🟡 **Gul = Måske** &nbsp;&nbsp;&nbsp; "
            "⬜ **Hvid = Ikke valgt**  \n"
            f"Vælg mindst **{min_sel}** datoer. "
            f"Din kvote denne måned: **{vol.get('required_shifts',2)} vagter**.")
    st.markdown("")

    prefs=render_pref_kalender(mkey,vid,rel_set,existing,mobile=mobile)
    markeret=sum(1 for p in prefs.values() if p)
    nok=markeret>=min_sel

    st.markdown("")
    ci,cb=st.columns([4,1])
    if markeret==0:
        ci.markdown("☝️ Klik på en dato for at markere.")
    elif nok:
        ci.markdown(f"✅ **{markeret}** datoer valgt — klar til at gemme!")
    else:
        ci.markdown(f"⚠️ **{markeret}** valgt — vælg mindst **{min_sel-markeret}** mere.")

    if cb.button("💾 Gem",type="primary",use_container_width=True,disabled=not nok):
        if mkey not in data["preferences"]:
            data["preferences"][mkey]={}
        data["preferences"][mkey][vid]={k:v for k,v in prefs.items() if v}
        save(data)
        st.success("✅ Dine ønsker er gemt! Du kan ændre dem igen, inden vagtplanen genereres.")
        st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
#  ADMIN-SIDE
# ══════════════════════════════════════════════════════════════════════════════
def side_admin(data:dict):
    # Mobil-blokering (CSS-baseret banner)
    st.markdown(
        '<div class="mobile-warn" style="background:#fff3e0;border:2px solid #ff9800;'
        'border-radius:10px;padding:16px;text-align:center;font-size:15px;'
        'font-weight:600;color:#e65100">⚠️ Administratorpanelet er ikke tilgængeligt på mobilenheder. '
        'Brug venligst en computer.</div>',
        unsafe_allow_html=True)

    if "admin_ok" not in st.session_state: st.session_state.admin_ok=False

    if not st.session_state.admin_ok:
        st.markdown("## 🔒 Administratorlogin")
        pwd=st.text_input("Adgangskode",type="password",placeholder="Skriv adgangskode...")
        if st.button("🔓 Log ind",type="primary"):
            if pwd==data.get("admin_password","plexus2024"):
                st.session_state.admin_ok=True; st.rerun()
            else:
                st.error("❌ Forkert adgangskode.")
        return

    with st.container():
        col_h,col_b=st.columns([5,1])
        col_h.markdown("## ⚙️ Administration")
        col_b.markdown('<div style="margin-top:18px"></div>',unsafe_allow_html=True)
        if col_b.button("🚪 Log ud",use_container_width=True):
            st.session_state.admin_ok=False; st.rerun()

    t1,t2,t3,t4=st.tabs(["👥 Frivillige","📅 Måneds-opsætning","⚡ Vagttildeling","📊 Resultater"])
    with t1: _tab_frivillige(data)
    with t2: _tab_opstaetning(data)
    with t3: _tab_tildeling(data)
    with t4: _tab_resultater(data)

# ── Tab: Frivillige ────────────────────────────────────────────────────────────
def _tab_frivillige(data:dict):
    st.markdown("### 👥 Administrer frivillige")

    with st.expander("➕ Tilføj ny frivillig",expanded=not data["volunteers"]):
        with st.form("add_vol",clear_on_submit=True):
            c1,c2,c3=st.columns([3,1,1])
            navn =c1.text_input("Navn")
            kvote=c2.number_input("Vagter/md.",1,20,2)
            aktiv_udv=c3.checkbox("Aktivitetsudvalg")
            if st.form_submit_button("✅ Tilføj"):
                if navn.strip():
                    nid=str(data.get("next_id",1))
                    data["volunteers"][nid]={
                        "name":navn.strip(),"required_shifts":int(kvote),
                        "active":True,"aktivitetsudvalg":bool(aktiv_udv)}
                    data["next_id"]=int(nid)+1
                    save(data); st.success(f"✅ {navn.strip()} er tilføjet!"); st.rerun()
                else:
                    st.warning("Angiv et navn.")

    if not data["volunteers"]:
        st.info("Ingen frivillige oprettet endnu."); return

    h1,h2,h3,h4,h5=st.columns([3,1,1,1,1])
    h1.markdown("**Navn**"); h2.markdown("**Vgt/md.**")
    h3.markdown("**Aktiv**"); h4.markdown("**Akt.udv.**")
    st.markdown("---")

    edits={}
    for vid,vol in sorted(data["volunteers"].items(),key=lambda x:x[1]["name"]):
        c1,c2,c3,c4,c5=st.columns([3,1,1,1,1])
        c1.markdown(
            f'**{vol["name"]}**'
            +(f' <span style="background:#dbeafe;color:#1e3a8a;font-size:10px;'
              f'padding:1px 6px;border-radius:4px">🔵 Akt.</span>'
              if vol.get("aktivitetsudvalg") else ""),
            unsafe_allow_html=True)
        q=c2.number_input("",1,20,vol.get("required_shifts",2),
                          key=f"q_{vid}",label_visibility="collapsed")
        a=c3.checkbox("",vol.get("active",True),
                      key=f"a_{vid}",label_visibility="collapsed")
        ak=c4.checkbox("",vol.get("aktivitetsudvalg",False),
                       key=f"ak_{vid}",label_visibility="collapsed")
        edits[vid]={"required_shifts":int(q),"active":a,"aktivitetsudvalg":ak}
        if c5.button("🗑️",key=f"del_{vid}",help=f"Slet {vol['name']}"):
            del data["volunteers"][vid]; save(data); st.rerun()

    st.markdown("")
    if st.button("💾 Gem alle ændringer",type="primary",use_container_width=True):
        for vid,vals in edits.items():
            if vid in data["volunteers"]:
                data["volunteers"][vid].update(vals)
        save(data); st.success("✅ Alle ændringer er gemt!")

    st.markdown("---")
    with st.expander("🔑 Skift admin-adgangskode"):
        with st.form("pwd_form"):
            p1=st.text_input("Ny adgangskode",type="password")
            p2=st.text_input("Gentag",type="password")
            if st.form_submit_button("Gem"):
                if p1 and p1==p2:
                    data["admin_password"]=p1; save(data); st.success("✅ Adgangskode ændret.")
                else:
                    st.error("Adgangskoderne matcher ikke.")

# ── Tab: Måneds-opsætning ──────────────────────────────────────────────────────
def _tab_opstaetning(data:dict):
    st.markdown("### 📅 Måneds-opsætning")

    ny,nm=next_plan_month(data)
    c1,c2=st.columns(2)
    år =int(c1.number_input("År",2024,2030,ny))
    mdr=int(c2.selectbox("Måned",range(1,13),index=nm-1,format_func=lambda x:MÅNEDER[x]))

    mkey=mk(år,mdr)
    cfg=data["monthly_config"].get(mkey,{})
    locked=cfg.get("released",False)

    st.markdown(f"#### {MÅNEDER[mdr]} {år}")
    st.markdown("---")

    if locked:
        st.success(f"✅ **{MÅNEDER[mdr]} {år}** er frigivet og låst.")
        y,m_=int(mkey[:4]),int(mkey[5:7])
        dt=cfg_date_types(cfg,y,m_)
        n_open =sum(1 for t in dt.values() if t==OPEN)
        n_act  =sum(1 for t in dt.values() if t==ACTIVITY)
        n_closed=sum(1 for t in dt.values() if t==CLOSED)
        col1,col2,col3=st.columns(3)
        col1.metric("🟢 Åbningsdage",n_open)
        col2.metric("🔵 Aktivitetsdage",n_act)
        col3.metric("🔴 Lukkede dage",n_closed)

        prefs_m=data["preferences"].get(mkey,{})
        aktive =sum(1 for v in data["volunteers"].values() if v.get("active",True))
        st.info(f"📊 **{len(prefs_m)}/{aktive}** aktive frivillige har indsendt ønsker.")

        if "confirm_revoke" not in st.session_state:
            st.session_state.confirm_revoke=None
        if st.button("🔓 Tilbagekald frigivelse",use_container_width=True):
            st.session_state.confirm_revoke=mkey
        if st.session_state.confirm_revoke==mkey:
            st.error(
                f"⚠️ **Advarsel!** Dette sletter **alle indsendte ønsker** og eventuelle "
                f"tildelte vagter for **{MÅNEDER[mdr]} {år}**. "
                "Du kan frigive måneden igen bagefter. Er du sikker?")
            ca,cb_=st.columns(2)
            if ca.button("✅ Ja, tilbagekald",type="primary",use_container_width=True):
                data["monthly_config"][mkey]["released"]=False
                data["preferences"].pop(mkey,None)
                data["assignments"].pop(mkey,None)
                st.session_state.pop(f"sc_{mkey}",None)
                st.session_state.confirm_revoke=None
                save(data); st.success("✅ Frigivelse er tilbagekaldt."); st.rerun()
            if cb_.button("❌ Annuller",use_container_width=True):
                st.session_state.confirm_revoke=None; st.rerun()
        return

    # ── Initialiser session state fra eksisterende config ─────────────────────
    sk=f"sc_{mkey}"
    if sk not in st.session_state:
        if "date_types" in cfg:
            st.session_state[sk]=dict(cfg["date_types"])
        else:
            st.session_state[sk]=default_date_types(år,mdr)

    st.markdown(
        "**Klik på en dato for at skifte type:**  \n"
        "🟢 **Åben** → 🔴 **Lukket** → 🔵 **Aktivitet** → 🟢 **Åben**  \n"
        "*(Man/Tirs/Ons/Søn er åbne som standard)*")
    st.markdown("")

    selected=render_setup_kalender(mkey)

    st.markdown("---")
    c3,c4,c5=st.columns(3)
    min_per=c3.number_input("👤 Min. frivillige/vagt",1,10,cfg.get("min_per_shift",3))
    max_per=c4.number_input("👥 Max. frivillige/vagt",1,20,cfg.get("max_per_shift",6))
    min_sel=c5.number_input("☑️ Min. ønsker/frivillig",1,20,cfg.get("min_selections",5))

    st.markdown("")
    cs,cr=st.columns(2)
    if cs.button("💾 Gem (ikke frigivet endnu)",use_container_width=True):
        data["monthly_config"][mkey]={
            "date_types":selected,
            "dates":[d for d,t in selected.items() if t in(OPEN,ACTIVITY)],
            "min_per_shift":int(min_per),"max_per_shift":int(max_per),
            "min_selections":int(min_sel),"released":False}
        save(data); st.success(f"✅ Opsætning for {MÅNEDER[mdr]} {år} er gemt.")

    if cr.button("🚀 Frigiv til frivillige",type="primary",use_container_width=True):
        active_dates=[d for d,t in selected.items() if t in(OPEN,ACTIVITY)]
        if not active_dates:
            st.error("Vælg mindst én åben eller aktivitetsdag inden frigivelse.")
        else:
            data["monthly_config"][mkey]={
                "date_types":selected,
                "dates":active_dates,
                "min_per_shift":int(min_per),"max_per_shift":int(max_per),
                "min_selections":int(min_sel),"released":True}
            save(data)
            st.success(f"🎉 **{MÅNEDER[mdr]} {år}** er frigivet til de frivillige!"); st.rerun()

    prefs_m=data["preferences"].get(mkey,{})
    aktive =sum(1 for v in data["volunteers"].values() if v.get("active",True))
    if aktive:
        st.info(f"📊 **{len(prefs_m)}/{aktive}** aktive frivillige har indsendt ønsker.")

# ── Tab: Vagttildeling ─────────────────────────────────────────────────────────
def _tab_tildeling(data:dict):
    st.markdown("### ⚡ Automatisk vagttildeling")

    frigivne=sorted(k for k,c in data["monthly_config"].items() if c.get("released"))
    if not frigivne:
        st.warning("📭 Ingen måneder er frigivet endnu."); return

    ny,nm=next_plan_month(data)
    default_mk=mk(ny,nm)
    default_idx=frigivne.index(default_mk) if default_mk in frigivne else 0

    mkey   =st.selectbox("Vælg måned",frigivne,index=default_idx,format_func=mk_label)
    prefs_m=data["preferences"].get(mkey,{})
    aktive ={vid:v for vid,v in data["volunteers"].items() if v.get("active",True)}

    c1,c2=st.columns(2)
    c1.metric("📋 Indsendte ønsker",f"{len(prefs_m)}/{len(aktive)}")

    col_ja,col_nej=st.columns(2)
    with col_ja:
        st.markdown("**✅ Klar:**")
        for vid,v in aktive.items():
            if vid in prefs_m:
                s =sum(1 for p in prefs_m[vid].values() if p=="sikker")
                ms=sum(1 for p in prefs_m[vid].values() if p=="måske")
                akt_badge=" 🔵" if v.get("aktivitetsudvalg") else ""
                st.write(f"• {v['name']}{akt_badge}  *(Ja: {s} / Måske: {ms})*")
    with col_nej:
        st.markdown("**❌ Mangler endnu:**")
        for vid,v in aktive.items():
            if vid not in prefs_m:
                st.write(f"• {v['name']}")

    st.markdown("---")
    allerede=mkey in data.get("assignments",{})

    if allerede:
        st.info("ℹ️ Vagter er allerede tildelt for denne måned.")
        if "confirm_reassign" not in st.session_state:
            st.session_state.confirm_reassign=None
        if st.button("🔄 Tildel vagter igen",use_container_width=True):
            st.session_state.confirm_reassign=mkey
        if st.session_state.confirm_reassign==mkey:
            st.warning(
                f"⚠️ **Advarsel!** Dette overskriver den eksisterende vagtplan for "
                f"**{mk_label(mkey)}**. Er du sikker?")
            ca,cb_=st.columns(2)
            if ca.button("✅ Ja, tildel igen",type="primary",use_container_width=True):
                if not prefs_m:
                    st.error("Ingen frivillige har indsendt ønsker.")
                else:
                    data=auto_assign(data,mkey); save(data)
                    st.session_state.confirm_reassign=None
                    st.success("🎉 Vagter er tildelt igen!"); st.balloons(); st.rerun()
            if cb_.button("❌ Annuller",use_container_width=True):
                st.session_state.confirm_reassign=None; st.rerun()
    else:
        if st.button("🚀 Tildel vagter automatisk",type="primary",use_container_width=True):
            if not prefs_m:
                st.error("Ingen frivillige har indsendt ønsker endnu.")
            else:
                data=auto_assign(data,mkey); save(data)
                st.success("🎉 Vagter er tildelt!"); st.balloons(); st.rerun()

    # ── Fail-safe eksport ──────────────────────────────────────────────────────
    st.markdown("---")
    with st.expander("🛡️ Fail-safe: Download rådata for denne måned"):
        st.caption(
            "Hent alle indsendte ønsker som CSV — tilgængeligt uanset om "
            "vagter er tildelt eller ej.")
        if prefs_m:
            rows=["Frivillig,Dato,Dag,Ønske"]
            vols=data["volunteers"]
            for vid,prefs in prefs_m.items():
                navn=vols.get(vid,{}).get("name",vid)
                for d_str,val in sorted(prefs.items()):
                    d=date.fromisoformat(d_str)
                    dag=DAG_LANG[d.weekday()]
                    rows.append(f"{navn},{d_str},{dag},{val}")
            st.download_button(
                "⬇️ Download ønsker som CSV",
                "\n".join(rows).encode("utf-8-sig"),
                f"plexus_rawdata_{mkey}.csv","text/csv",
                use_container_width=True)
        else:
            st.info("Ingen ønsker indsendt endnu for denne måned.")

# ── Tab: Resultater ────────────────────────────────────────────────────────────
def _tab_resultater(data:dict):
    st.markdown("### 📊 Resultater")

    tildelte=sorted(data.get("assignments",{}).keys(),reverse=True)
    if not tildelte:
        st.info("📭 Ingen vagter er tildelt endnu."); return

    mkey=st.selectbox("Vælg måned",tildelte,format_func=mk_label)
    asgn=data["assignments"][mkey]
    vols=data["volunteers"]

    st.caption(f"⏱️ Genereret: {asgn.get('generated_at','–')}")

    åbne   =len(asgn["open"])
    lukkede=len(asgn["closed"])
    aktivit=len(asgn.get("activity",[]))
    total  =åbne+lukkede
    pct    =round(100*åbne/total) if total>0 else 0

    c1,c2,c3,c4=st.columns(4)
    c1.metric("🟢 Åbningsdage",åbne)
    c2.metric("🔵 Aktivitetsdage",aktivit)
    c3.metric("🔴 Lukkedage",lukkede)
    c4.metric("📈 Åbningspct.",f"{pct}%")

    if asgn.get("unmet_quota"):
        with st.expander("⚠️ Frivillige med ufyldt kvote"):
            for vid,mangler in asgn["unmet_quota"].items():
                st.write(f"• **{vols.get(vid,{}).get('name',vid)}** mangler {mangler} vagt(er)")

    st.markdown("### 📅 Kalender-oversigt")
    st.markdown(
        cal_static_resultater(mkey,asgn["shifts"],asgn["open"],asgn["closed"],
                               asgn.get("activity",[]),vols),
        unsafe_allow_html=True)

    st.markdown("")
    with st.expander("👤 Oversigt per frivillig"):
        for vid,vol in sorted(vols.items(),key=lambda x:x[1]["name"]):
            if not vol.get("active"): continue
            mine   =sorted(d for d,vs in asgn["shifts"].items() if vid in vs)
            kraevet=vol.get("required_shifts",2)
            ikon   ="✅" if len(mine)>=kraevet else "⚠️"
            akt    =" 🔵" if vol.get("aktivitetsudvalg") else ""
            st.markdown(f"**{ikon} {vol['name']}{akt}** — {len(mine)}/{kraevet} vagter")
            for d in mine:
                type_tag="🔵" if d in asgn.get("activity",[]) else "🟢"
                st.write(f"  • {type_tag} {full_date_str(d)}")
            if len(mine)<kraevet:
                st.caption(f"  Fik {kraevet-len(mine)} færre end aftalt.")

    # Eksport
    rækker=["Dato,Dag,Status,Type,Frivillige"]
    for d in sorted(asgn["shifts"]):
        navne="; ".join(vols[v]["name"] for v in asgn["shifts"][d] if v in vols)
        status="Åben" if d in asgn["open"] else "Lukket"
        ttype ="Aktivitet" if d in asgn.get("activity",[]) else "Normal"
        rækker.append(f"{d},{DAG_LANG[date.fromisoformat(d).weekday()]},{status},{ttype},{navne}")

    st.markdown("")
    st.download_button(
        "⬇️ Download vagtplan som CSV",
        "\n".join(rækker).encode("utf-8-sig"),
        f"plexus_vagtplan_{mkey}.csv","text/csv",
        use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    st.set_page_config(
        page_title="Plexus Vagtplan",page_icon="📅",layout="wide",
        initial_sidebar_state="expanded")
    st.markdown(CSS,unsafe_allow_html=True)
    data=load()

    with st.sidebar:
        st.markdown("## 📅 Plexus Vagtplan")
        st.divider()
        side=st.radio("",["🙋 Frivillig","⚙️ Administrator"],label_visibility="hidden")
        st.divider()
        st.caption(f"Version {VERSION}")
        st.caption("Lavet af Fabian Salvatore")

    if side=="🙋 Frivillig":
        side_frivillig(data)
    else:
        side_admin(data)

if __name__=="__main__":
    main()

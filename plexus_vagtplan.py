# -*- coding: utf-8 -*-
"""
Plexus Vagtplan
Lavet af Fabian Salvatore
"""
import streamlit as st
import json, os, calendar
from datetime import date, datetime

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
SETUP_CYCLE = {OPEN:CLOSED, CLOSED:ACTIVITY, ACTIVITY:OPEN}
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

# ── Data ──────────────────────────────────────────────────────────────────────
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
def mk_label(k)->str: y,m=k.split("-"); return f"{MÅNEDER[int(m)]} {y}"
def full_dato(d_str:str)->str:
    d=date.fromisoformat(d_str)
    return f"{DAG_LANG[d.weekday()]} den {d.day}. {MÅN_GEN[d.month]}"

def default_date_types(y:int,m:int)->dict:
    n=calendar.monthrange(y,m)[1]
    return {date(y,m,d).isoformat():
            (OPEN if date(y,m,d).weekday() in VAGTDAG_IDX else CLOSED)
            for d in range(1,n+1)}

def get_date_types(cfg:dict,y:int,m:int)->dict:
    if "date_types" in cfg: return cfg["date_types"]
    return {d:OPEN for d in cfg.get("dates",[])}

def next_plan_month(data:dict)->tuple:
    assigned=sorted(data.get("assignments",{}).keys())
    if assigned:
        y,m=int(assigned[-1][:4]),int(assigned[-1][5:7])
    else:
        now=datetime.now(); y,m=now.year,now.month
    return (y+1,1) if m==12 else (y,m+1)

# ── Kalender-hjælpere ─────────────────────────────────────────────────────────
def _dag_header(border_color:str,text_color:str):
    cols=st.columns(7)
    for i in range(7):
        is_vd=i in VAGTDAG_IDX
        cols[i].markdown(
            f'<div style="text-align:center;font-size:11px;font-weight:700;'
            f'padding:5px 0;letter-spacing:0.5px;text-transform:uppercase;'
            f'border-bottom:3px solid {"" if not is_vd else border_color};'
            f'color:{text_color if is_vd else "#ccc"}">'
            f'{DAG_LANG[i][:3]}</div>',unsafe_allow_html=True)

def _colored_cell(bg:str,border:str,text:str,
                   dag:str,day:int,maan:str,status:str):
    """Farvet celle – vises OVER knappen."""
    st.markdown(
        f'<div style="background:{bg};border:2px solid {border};'
        f'border-radius:10px 10px 0 0;padding:8px 4px 6px;text-align:center;'
        f'min-height:84px">'
        f'<div style="font-size:9px;font-weight:700;color:{text};'
        f'text-transform:uppercase;letter-spacing:0.4px">{dag}</div>'
        f'<div style="font-size:26px;font-weight:900;color:{text};line-height:1.1">{day}</div>'
        f'<div style="font-size:9px;color:{text};opacity:0.8">{maan}</div>'
        f'<div style="font-size:11px;font-weight:600;color:{text};margin-top:3px">{status}</div>'
        f'</div>',unsafe_allow_html=True)

def _grey_cell(dag:str,day:int,maan:str,label:str=""):
    """Grå, ikke-klikbar celle."""
    st.markdown(
        f'<div style="background:#f0f0f0;border:1px dashed #ccc;'
        f'border-radius:10px;padding:8px 4px 6px;text-align:center;'
        f'min-height:84px;color:#bbb">'
        f'<div style="font-size:9px;font-weight:700;text-transform:uppercase">{dag}</div>'
        f'<div style="font-size:26px;font-weight:900;line-height:1.1">{day}</div>'
        f'<div style="font-size:9px;opacity:0.8">{maan}</div>'
        f'<div style="font-size:11px;margin-top:3px">{label}</div>'
        f'</div>',unsafe_allow_html=True)

def _empty_cell():
    st.markdown('<div style="min-height:110px"></div>',unsafe_allow_html=True)

# ── Fordelingsalgoritme ───────────────────────────────────────────────────────
def auto_assign(data:dict,mkey:str)->dict:
    cfg        = data["monthly_config"].get(mkey,{})
    y,m        = int(mkey[:4]),int(mkey[5:7])
    dt         = get_date_types(cfg,y,m)
    active_d   = [d for d,t in dt.items() if t in (OPEN,ACTIVITY)]
    min_per    = cfg.get("min_per_shift",3)
    max_per    = cfg.get("max_per_shift",3)
    prefs_m    = data["preferences"].get(mkey,{})
    vols       = data["volunteers"]
    active     = [vid for vid,v in vols.items() if v.get("active",True)]
    is_akt     = {vid:vols[vid].get("aktivitetsudvalg",False) for vid in active}

    prio={vid:{d:(2 if prefs_m.get(vid,{}).get(d)=="sikker"
                  else 1 if prefs_m.get(vid,{}).get(d)=="måske" else 0)
               for d in active_d}
          for vid in active}

    remaining={vid:vols[vid].get("required_shifts",2) for vid in active}
    shifts={d:[] for d in active_d}

    def cand_groups(d):
        if dt.get(d)==ACTIVITY:
            return [
                [v for v in active if is_akt[v]     and prio[v][d]==2],
                [v for v in active if is_akt[v]     and prio[v][d]==1],
                [v for v in active if not is_akt[v] and prio[v][d]==2],
                [v for v in active if not is_akt[v] and prio[v][d]==1],
            ]
        return [
            [v for v in active if prio[v][d]==2],
            [v for v in active if prio[v][d]==1],
        ]

    sorted_dates=sorted(active_d,key=lambda d:sum(1 for v in active if prio[v][d]>0))

    # Fase 1: opnå min_per_shift
    for d in sorted_dates:
        if len(shifts[d])>=min_per: continue
        for grp in cand_groups(d):
            cands=[v for v in grp if remaining[v]>0 and v not in shifts[d] and len(shifts[d])<max_per]
            cands.sort(key=lambda v:remaining[v],reverse=True)
            for v in cands:
                if len(shifts[d])>=min_per: break
                shifts[d].append(v); remaining[v]-=1

    # Fase 2: fair round-robin fordeling af resterende kvote
    vol_open={vid:sum(1 for d in active_d if vid in shifts[d]) for vid in active}
    any_assigned=True
    while any_assigned:
        any_assigned=False
        for vid in sorted(active,key=lambda v:(remaining[v],-vol_open[v]),reverse=True):
            if remaining[vid]<=0: continue
            cands=[d for d in active_d
                   if prio[vid][d]>0 and vid not in shifts[d] and len(shifts[d])<max_per]
            if not cands: continue
            cands.sort(key=lambda d:(len(shifts[d])>=min_per,-prio[vid][d],len(shifts[d])))
            shifts[cands[0]].append(vid); remaining[vid]-=1; vol_open[vid]+=1
            any_assigned=True; break

    open_d    =[d for d in active_d if len(shifts[d])>=min_per]
    closed_d  =[d for d in active_d if len(shifts[d])<min_per]+[d for d,t in dt.items() if t==CLOSED]
    activity_d=[d for d in active_d if dt.get(d)==ACTIVITY]

    data["assignments"][mkey]={
        "shifts":shifts,"open":open_d,"closed":closed_d,"activity":activity_d,
        "unmet_quota":{v:remaining[v] for v in active if remaining[v]>0},
        "generated_at":datetime.now().strftime("%d/%m/%Y %H:%M"),
    }
    return data

# ══════════════════════════════════════════════════════════════════════════════
#  STATISK HTML-KALENDER (resultater + frivillig vagtplan)
# ══════════════════════════════════════════════════════════════════════════════
def _html_thead()->str:
    cells="".join(
        f'<th style="padding:10px 4px;font-size:12px;font-weight:700;'
        f'letter-spacing:0.5px;border:1px solid #e0e0e0;'
        f'background:{"#f0f7ff" if i in VAGTDAG_IDX else "#f9f9f9"};'
        f'color:{"#1565c0" if i in VAGTDAG_IDX else "#bbb"};'
        f'border-bottom:3px solid {"#1565c0" if i in VAGTDAG_IDX else "#e0e0e0"}">'
        f'{DAG_LANG[i]}</th>'
        for i in range(7))
    return f"<thead><tr>{cells}</tr></thead>"

def cal_html_resultater(mkey:str,shifts:dict,open_days:list,closed_days:list,
                         activity_days:list,vols:dict,highlight_vid:str=None)->str:
    y,m=int(mkey[:4]),int(mkey[5:7])
    rows=""
    for week in calendar.monthcalendar(y,m):
        rows+="<tr>"
        for i,day in enumerate(week):
            if day==0:
                rows+=('<td style="background:#fafafa;border:1px solid #ececec;'
                       'padding:6px;min-width:100px"></td>')
                continue
            d_str=date(y,m,day).isoformat()
            is_vdag=i in VAGTDAG_IDX
            if is_vdag:
                is_open=d_str in open_days
                is_act =d_str in activity_days
                navne  =[(v,vols[v]["name"]) for v in shifts.get(d_str,[]) if v in vols]
                if is_act and is_open:
                    bg,hdr,dot="#dbeafe","#0d47a1","🔵"
                elif is_open:
                    bg,hdr,dot="#e8f5e9","#1b5e20","🟢"
                else:
                    bg,hdr,dot="#ffebee","#b71c1c","🔴"
                names_html="".join(
                    f'<div style="font-size:11px;margin-top:2px;padding:1px 6px;'
                    f'border-radius:4px;'
                    f'background:{"#a5d6a7" if vid==highlight_vid else "#ffffffcc"};'
                    f'color:{"#1b5e20" if vid==highlight_vid else "#333"};'
                    f'font-weight:{"700" if vid==highlight_vid else "400"}">'
                    f'{"★ " if vid==highlight_vid else ""}{name}</div>'
                    for vid,name in navne)
                rows+=(f'<td style="background:{bg};border:1px solid #ccc;'
                       f'padding:8px 5px;vertical-align:top;min-width:100px">'
                       f'<div style="font-size:10px;font-weight:700;color:{hdr}">'
                       f'{DAG_LANG[i]}</div>'
                       f'<div style="font-size:22px;font-weight:900;color:{hdr};line-height:1">{day}</div>'
                       f'<div style="font-size:9px;color:{hdr};margin-bottom:2px">{MÅN_GEN[m]}</div>'
                       f'<div style="font-size:10px;color:{hdr}">{dot}</div>'
                       f'{names_html}</td>')
            else:
                rows+=(f'<td style="background:#fafafa;border:1px solid #ececec;'
                       f'padding:8px 4px;text-align:center;color:#ccc;vertical-align:top">'
                       f'<div style="font-size:11px">{DAG_LANG[i]}</div>'
                       f'<div style="font-size:16px">{day}</div></td>')
        rows+="</tr>"
    return (f'<div style="overflow-x:auto;border-radius:12px;border:1px solid #e0e0e0;overflow:hidden">'
            f'<table style="border-collapse:collapse;width:100%;table-layout:fixed">'
            +_html_thead()+f"<tbody>{rows}</tbody></table></div>")

# ══════════════════════════════════════════════════════════════════════════════
#  INTERAKTIV SETUP-KALENDER
# ══════════════════════════════════════════════════════════════════════════════
def render_setup_kalender(mkey:str)->dict:
    y,m=int(mkey[:4]),int(mkey[5:7])
    sk=f"sc_{mkey}"
    if sk not in st.session_state:
        cfg=st.session_state.get(f"cfg_{mkey}",{})
        if "date_types" in cfg:
            st.session_state[sk]=dict(cfg["date_types"])
        else:
            st.session_state[sk]=default_date_types(y,m)

    _dag_header("#2e7d32","#2e7d32")

    for week in calendar.monthcalendar(y,m):
        cols=st.columns(7)
        for i,day in enumerate(week):
            with cols[i]:
                if day==0:
                    _empty_cell(); continue
                d_str=date(y,m,day).isoformat()
                state=st.session_state[sk].get(d_str,CLOSED)
                bg,border,text,icon,label=SETUP_STYLE[state]
                next_s=SETUP_CYCLE[state]
                _,_,_,n_icon,n_label=SETUP_STYLE[next_s]
                _colored_cell(bg,border,text,DAG_LANG[i][:3],day,MÅN_GEN[m][:3],
                               f"{icon} {label}")
                if st.button(f"→ {n_icon} {n_label}",
                             key=f"sc_{mkey}_{d_str}",use_container_width=True):
                    st.session_state[sk][d_str]=next_s; st.rerun()

    return dict(st.session_state[sk])

# ══════════════════════════════════════════════════════════════════════════════
#  INTERAKTIV PRÆFERENCE-KALENDER
# ══════════════════════════════════════════════════════════════════════════════
def render_pref_kalender(mkey:str,vid:str,date_types:dict,existing:dict)->dict:
    y,m=int(mkey[:4]),int(mkey[5:7])
    sk=f"vp_{mkey}_{vid}"
    if sk not in st.session_state:
        st.session_state[sk]=dict(existing)

    rel_set={d for d,t in date_types.items() if t in (OPEN,ACTIVITY)}

    _dag_header("#1565c0","#1565c0")

    for week in calendar.monthcalendar(y,m):
        cols=st.columns(7)
        for i,day in enumerate(week):
            with cols[i]:
                if day==0:
                    _empty_cell(); continue
                d_str  =date(y,m,day).isoformat()
                is_vdag=i in VAGTDAG_IDX
                is_rel =d_str in rel_set
                is_cl  =date_types.get(d_str)==CLOSED

                if is_vdag and is_rel:
                    state=st.session_state[sk].get(d_str,"")
                    bg,border,text,icon,label=PREF_STYLE[state]
                    next_s=PREF_CYCLE[state]
                    _,_,_,n_icon,n_label=PREF_STYLE[next_s]
                    _colored_cell(bg,border,text,DAG_LANG[i][:3],day,MÅN_GEN[m][:3],
                                   f"{icon} {label}")
                    if st.button(f"→ {n_icon} {n_label}",
                                 key=f"vp_{mkey}_{vid}_{d_str}",use_container_width=True):
                        st.session_state[sk][d_str]=next_s; st.rerun()
                elif is_vdag and is_cl:
                    _grey_cell(DAG_LANG[i][:3],day,MÅN_GEN[m][:3],"🔴 Lukket")
                    st.markdown('<div style="height:31px"></div>',unsafe_allow_html=True)
                else:
                    _empty_cell()

    return dict(st.session_state[sk])

# ══════════════════════════════════════════════════════════════════════════════
#  MOBILVENLIG PRÆFERENCE-KALENDER
# ══════════════════════════════════════════════════════════════════════════════
def render_pref_mobil(mkey:str,vid:str,date_types:dict,existing:dict)->dict:
    sk=f"vp_{mkey}_{vid}"
    if sk not in st.session_state:
        st.session_state[sk]=dict(existing)

    rel_dates=sorted(d for d,t in date_types.items() if t in (OPEN,ACTIVITY))
    if not rel_dates:
        st.info("Ingen datoer at vælge endnu."); return dict(st.session_state[sk])

    for i in range(0,len(rel_dates),3):
        batch=rel_dates[i:i+3]
        cols=st.columns(3)
        for ci,d_str in enumerate(batch):
            d=date.fromisoformat(d_str)
            state=st.session_state[sk].get(d_str,"")
            bg,border,text,icon,label=PREF_STYLE[state]
            next_s=PREF_CYCLE[state]
            _,_,_,n_icon,n_label=PREF_STYLE[next_s]
            with cols[ci]:
                _colored_cell(bg,border,text,DAG_LANG[d.weekday()][:3],
                               d.day,MÅN_GEN[d.month][:3],f"{icon} {label}")
                if st.button(f"→ {n_icon} {n_label}",
                             key=f"mob_{mkey}_{vid}_{d_str}",use_container_width=True):
                    st.session_state[sk][d_str]=next_s; st.rerun()

    return dict(st.session_state[sk])

# ══════════════════════════════════════════════════════════════════════════════
#  FRIVILLIG-SIDE
# ══════════════════════════════════════════════════════════════════════════════
def side_frivillig(data:dict):
    if "vol_id" not in st.session_state: st.session_state.vol_id=None

    active_vols={vid:v for vid,v in data["volunteers"].items() if v.get("active",True)}

    if st.session_state.vol_id is None:
        st.markdown("## 📅 Plexus Vagtplan")
        st.markdown("### 👋 Hvem er du?")
        st.caption("Vælg dit navn for at se din vagtplan eller indsende ønsker.")
        if not active_vols:
            st.info("Ingen frivillige er oprettet endnu. Kontakt administratoren."); return
        navne={v["name"]:vid for vid,v in sorted(active_vols.items(),key=lambda x:x[1]["name"])}
        valgt=st.selectbox("",["— Vælg dit navn —"]+list(navne.keys()),
                           label_visibility="collapsed",key="vol_name_select")
        if valgt!="— Vælg dit navn —":
            st.session_state.vol_id=navne[valgt]; st.rerun()
        return

    vid=st.session_state.vol_id
    if vid not in data["volunteers"]:
        st.session_state.vol_id=None; st.rerun()

    vol=data["volunteers"][vid]
    st.markdown('<div style="margin-top:30px"></div>',unsafe_allow_html=True)
    col_h,col_b=st.columns([5,1])
    col_h.markdown(f"## 👋 Hej, {vol['name']}!")
    if col_b.button("← Skift",use_container_width=True,key="skift_btn"):
        st.session_state.vol_id=None; st.rerun()
    st.divider()

    released={k for k,c in data["monthly_config"].items() if c.get("released")}
    assigned =set(data.get("assignments",{}).keys())
    alle     =sorted(released|assigned,reverse=True)

    if not alle:
        st.info("📭 Ingen måneder er tilgængelige endnu."); return

    sel_mk=st.selectbox("📅 Vælg periode",alle,index=0,
                        format_func=mk_label,key="vol_month_select")
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
    c1.metric("✅ Dine vagter",  f"{len(my_shifts)}/{kraevet}")
    c2.metric("🟢 Åbningsdage", len(asgn["open"]))
    c3.metric("🔴 Lukkedage",   len(asgn["closed"]))

    st.markdown("### 📅 Vagtplan")
    st.markdown(
        cal_html_resultater(mkey,asgn["shifts"],asgn["open"],asgn["closed"],
                             asgn.get("activity",[]),data["volunteers"],highlight_vid=vid),
        unsafe_allow_html=True)
    if my_shifts:
        st.markdown("---")
        st.markdown("**🗓️ Dine vagter:**")
        for d in my_shifts:
            st.success(f"  ✅ {full_dato(d)}")
    else:
        st.info("Du er ikke tildelt vagter denne måned.")
    if len(my_shifts)<kraevet:
        st.warning(f"⚠️ Du fik {kraevet-len(my_shifts)} færre vagt(er) end aftalt.")

def _vis_praeference(data:dict,vid:str,vol:dict,mkey:str):
    cfg     =data["monthly_config"][mkey]
    y,m     =int(mkey[:4]),int(mkey[5:7])
    dt      =get_date_types(cfg,y,m)
    min_sel =cfg.get("min_selections",5)
    existing=data["preferences"].get(mkey,{}).get(vid,{})

    if data["preferences"].get(mkey,{}).get(vid):
        st.success("✅ Du har allerede gemt dine ønsker — du kan ændre dem nedenfor.")

    st.markdown(f"### ✏️ Vagtønsker – {mk_label(mkey)}")
    st.markdown(
        "Klik på en dato for at skifte:  \n"
        "**✅ Grøn = Ja** &nbsp;|&nbsp; **🟡 Gul = Måske** &nbsp;|&nbsp; **⬜ = Ikke valgt**  \n"
        f"Lukkede dage er grå. Vælg mindst **{min_sel}** datoer. "
        f"Din kvote: **{vol.get('required_shifts',2)} vagter**.")

    mobile=st.toggle("📱 Mobilvenlig visning (3 kolonner)",key="mob_tog",value=False)
    st.markdown("")

    if mobile:
        prefs=render_pref_mobil(mkey,vid,dt,existing)
    else:
        prefs=render_pref_kalender(mkey,vid,dt,existing)

    markeret=sum(1 for p in prefs.values() if p)
    nok=markeret>=min_sel

    st.markdown("")
    ci,cb=st.columns([4,1])
    if markeret==0:
        ci.markdown("☝️ Klik på en dato ovenfor for at markere.")
    elif nok:
        ci.markdown(f"✅ **{markeret}** datoer valgt — klar til at gemme!")
    else:
        ci.markdown(f"⚠️ **{markeret}** valgt — vælg mindst **{min_sel-markeret}** mere.")

    if cb.button("💾 Gem",type="primary",use_container_width=True,
                 disabled=not nok,key="gem_prefs"):
        if mkey not in data["preferences"]: data["preferences"][mkey]={}
        data["preferences"][mkey][vid]={k:v for k,v in prefs.items() if v}
        save(data)
        st.success("✅ Dine ønsker er gemt! Du kan ændre dem igen inden vagtplanen genereres.")
        st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
#  ADMIN-SIDE
# ══════════════════════════════════════════════════════════════════════════════
def side_admin(data:dict):
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

    if "admin_ok" not in st.session_state: st.session_state.admin_ok=False

    if not st.session_state.admin_ok:
        st.markdown("## 🔒 Administratorlogin")
        pwd=st.text_input("Adgangskode",type="password",placeholder="Skriv adgangskode...")
        if st.button("🔓 Log ind",type="primary",key="login_btn"):
            if pwd==data.get("admin_password","plexus2024"):
                st.session_state.admin_ok=True; st.rerun()
            else:
                st.error("❌ Forkert adgangskode.")
        return

    st.markdown('<div style="margin-top:20px"></div>',unsafe_allow_html=True)
    col_h,col_b=st.columns([5,1])
    col_h.markdown("## ⚙️ Administration")
    if col_b.button("🚪 Log ud",use_container_width=True,key="logout_btn"):
        st.session_state.admin_ok=False; st.rerun()

    t1,t2,t3,t4=st.tabs([
        "👥 Frivillige","📅 Måneds-opsætning","⚡ Vagttildeling","📊 Resultater"])
    with t1: _tab_frivillige(data)
    with t2: _tab_opstaetning(data)
    with t3: _tab_tildeling(data)
    with t4: _tab_resultater(data)

# ── Tab: Frivillige ────────────────────────────────────────────────────────────
def _tab_frivillige(data:dict):
    st.markdown("### 👥 Frivillige")
    with st.expander("➕ Tilføj ny frivillig",expanded=not data["volunteers"]):
        with st.form("add_vol",clear_on_submit=True):
            c1,c2,c3=st.columns([3,1,1])
            navn =c1.text_input("Navn")
            kvote=c2.number_input("Vagter/md.",1,20,2)
            akt  =c3.checkbox("Aktivitetsudvalg")
            if st.form_submit_button("✅ Tilføj"):
                if navn.strip():
                    nid=str(data.get("next_id",1))
                    data["volunteers"][nid]={
                        "name":navn.strip(),"required_shifts":int(kvote),
                        "active":True,"aktivitetsudvalg":bool(akt)}
                    data["next_id"]=int(nid)+1
                    save(data); st.success(f"✅ {navn.strip()} er tilføjet!"); st.rerun()
                else: st.warning("Angiv et navn.")

    if not data["volunteers"]:
        st.info("Ingen frivillige oprettet endnu."); return

    h1,h2,h3,h4,_=st.columns([3,1,1,1,1])
    h1.markdown("**Navn**"); h2.markdown("**Vgt/md.**")
    h3.markdown("**Aktiv**"); h4.markdown("**Akt.udv.**"); st.markdown("---")

    edits={}
    for vid,vol in sorted(data["volunteers"].items(),key=lambda x:x[1]["name"]):
        c1,c2,c3,c4,c5=st.columns([3,1,1,1,1])
        badge=(f' <span style="background:#dbeafe;color:#1e3a8a;font-size:10px;'
               f'padding:1px 6px;border-radius:4px">🔵</span>'
               if vol.get("aktivitetsudvalg") else "")
        c1.markdown(f'**{vol["name"]}**{badge}',unsafe_allow_html=True)
        q=c2.number_input("",1,20,vol.get("required_shifts",2),
                          key=f"q_{vid}",label_visibility="collapsed")
        a=c3.checkbox("",vol.get("active",True),key=f"a_{vid}",label_visibility="collapsed")
        ak=c4.checkbox("",vol.get("aktivitetsudvalg",False),key=f"ak_{vid}",label_visibility="collapsed")
        edits[vid]={"required_shifts":int(q),"active":a,"aktivitetsudvalg":ak}
        if c5.button("🗑️",key=f"del_{vid}",help=f"Slet {vol['name']}"):
            del data["volunteers"][vid]; save(data); st.rerun()

    st.markdown("")
    if st.button("💾 Gem alle ændringer",type="primary",use_container_width=True,key="gem_alle"):
        for vid,vals in edits.items():
            if vid in data["volunteers"]: data["volunteers"][vid].update(vals)
        save(data); st.success("✅ Alle ændringer gemt!")

    st.markdown("---")
    with st.expander("🔑 Skift admin-adgangskode"):
        with st.form("pwd_form"):
            p1=st.text_input("Ny adgangskode",type="password")
            p2=st.text_input("Gentag",type="password")
            if st.form_submit_button("Gem"):
                if p1 and p1==p2:
                    data["admin_password"]=p1; save(data); st.success("✅ Adgangskode ændret.")
                else: st.error("Adgangskoderne matcher ikke.")

# ── Tab: Måneds-opsætning ──────────────────────────────────────────────────────
def _tab_opstaetning(data:dict):
    st.markdown("### 📅 Måneds-opsætning")
    ny,nm=next_plan_month(data)
    c1,c2=st.columns(2)
    år =int(c1.number_input("År",2024,2030,ny,key="setup_ar"))
    mdr=int(c2.selectbox("Måned",range(1,13),index=nm-1,
                          format_func=lambda x:MÅNEDER[x],key="setup_maaned"))

    mkey=mk(år,mdr)
    cfg=data["monthly_config"].get(mkey,{})
    locked=cfg.get("released",False)
    st.markdown(f"#### {MÅNEDER[mdr]} {år}")
    st.markdown("---")

    if locked:
        st.success(f"✅ **{MÅNEDER[mdr]} {år}** er frigivet og låst.")
        y_,m_=int(mkey[:4]),int(mkey[5:7])
        dt=get_date_types(cfg,y_,m_)
        c1,c2,c3=st.columns(3)
        c1.metric("🟢 Åbne",sum(1 for t in dt.values() if t==OPEN))
        c2.metric("🔵 Aktivitet",sum(1 for t in dt.values() if t==ACTIVITY))
        c3.metric("🔴 Lukkede",sum(1 for t in dt.values() if t==CLOSED))
        prefs_m=data["preferences"].get(mkey,{})
        aktive=sum(1 for v in data["volunteers"].values() if v.get("active",True))
        st.info(f"📊 **{len(prefs_m)}/{aktive}** aktive frivillige har indsendt ønsker.")

        if "confirm_revoke" not in st.session_state: st.session_state.confirm_revoke=None
        if st.button("🔓 Tilbagekald frigivelse",use_container_width=True,key="revoke_btn"):
            st.session_state.confirm_revoke=mkey
        if st.session_state.confirm_revoke==mkey:
            st.error(
                f"⚠️ **Advarsel!** Dette sletter alle indsendte ønsker og eventuelle "
                f"tildelte vagter for **{MÅNEDER[mdr]} {år}**. Er du sikker?")
            ca,cb_=st.columns(2)
            if ca.button("✅ Ja, tilbagekald",type="primary",use_container_width=True,key="ja_revoke"):
                data["monthly_config"][mkey]["released"]=False
                data["preferences"].pop(mkey,None); data["assignments"].pop(mkey,None)
                st.session_state.pop(f"sc_{mkey}",None)
                st.session_state.confirm_revoke=None
                save(data); st.success("✅ Frigivelse er tilbagekaldt."); st.rerun()
            if cb_.button("❌ Annuller",use_container_width=True,key="nej_revoke"):
                st.session_state.confirm_revoke=None; st.rerun()
        return

    sk=f"sc_{mkey}"
    if sk not in st.session_state:
        if "date_types" in cfg: st.session_state[sk]=dict(cfg["date_types"])
        else: st.session_state[sk]=default_date_types(år,mdr)

    st.markdown(
        "**Klik på pilen under en dato for at skifte type:**  \n"
        "🟢 **Åben** → 🔴 **Lukket** → 🔵 **Aktivitet** → 🟢 ...  \n"
        "*(Man/Tirs/Ons/Søn er åbne som standard)*")
    st.markdown("")

    selected=render_setup_kalender(mkey)

    st.markdown("---")
    c3,c4,c5=st.columns(3)
    # Standard: min=3, max=3, min_sel=5
    min_per=c3.number_input("👤 Min. frivillige/vagt",1,10,cfg.get("min_per_shift",3),key="min_per")
    max_per=c4.number_input("👥 Max. frivillige/vagt",1,20,cfg.get("max_per_shift",3),key="max_per")
    min_sel=c5.number_input("☑️ Min. ønsker/frivillig",1,20,cfg.get("min_selections",5),key="min_sel")

    st.markdown("")
    cs,cr=st.columns(2)
    if cs.button("💾 Gem (ikke frigivet)",use_container_width=True,key="gem_setup"):
        data["monthly_config"][mkey]={
            "date_types":selected,
            "dates":[d for d,t in selected.items() if t in (OPEN,ACTIVITY)],
            "min_per_shift":int(min_per),"max_per_shift":int(max_per),
            "min_selections":int(min_sel),"released":False}
        save(data); st.success(f"✅ Opsætning for {MÅNEDER[mdr]} {år} gemt.")

    if cr.button("🚀 Frigiv til frivillige",type="primary",use_container_width=True,key="frigiv_btn"):
        active_d=[d for d,t in selected.items() if t in (OPEN,ACTIVITY)]
        if not active_d:
            st.error("Vælg mindst én åben eller aktivitetsdag.")
        else:
            data["monthly_config"][mkey]={
                "date_types":selected,"dates":active_d,
                "min_per_shift":int(min_per),"max_per_shift":int(max_per),
                "min_selections":int(min_sel),"released":True}
            save(data); st.success(f"🎉 **{MÅNEDER[mdr]} {år}** er frigivet!"); st.rerun()

    prefs_m=data["preferences"].get(mkey,{})
    aktive=sum(1 for v in data["volunteers"].values() if v.get("active",True))
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

    mkey   =st.selectbox("Vælg måned",frigivne,index=default_idx,
                          format_func=mk_label,key="tildeling_month_select")
    prefs_m=data["preferences"].get(mkey,{})
    aktive ={vid:v for vid,v in data["volunteers"].items() if v.get("active",True)}

    c1,c2=st.columns(2)
    c1.metric("📋 Indsendte ønsker",f"{len(prefs_m)}/{len(aktive)}")

    col_ja,col_nej=st.columns(2)
    with col_ja:
        st.markdown("**✅ Klar:**")
        for vid,v in aktive.items():
            if vid in prefs_m:
                s=sum(1 for p in prefs_m[vid].values() if p=="sikker")
                ms=sum(1 for p in prefs_m[vid].values() if p=="måske")
                akt=" 🔵" if v.get("aktivitetsudvalg") else ""
                st.write(f"• {v['name']}{akt}  *(Ja: {s} / Måske: {ms})*")
    with col_nej:
        st.markdown("**❌ Mangler:**")
        for vid,v in aktive.items():
            if vid not in prefs_m: st.write(f"• {v['name']}")

    st.markdown("---")
    allerede=mkey in data.get("assignments",{})

    if allerede:
        st.info("ℹ️ Vagter er allerede tildelt for denne måned.")
        if "confirm_reassign" not in st.session_state: st.session_state.confirm_reassign=None
        if st.button("🔄 Omfordel vagter",use_container_width=True,key="reassign_btn"):
            st.session_state.confirm_reassign=mkey
        if st.session_state.confirm_reassign==mkey:
            st.warning(f"⚠️ Dette overskriver vagtplanen for **{mk_label(mkey)}**. Er du sikker?")
            ca,cb_=st.columns(2)
            if ca.button("✅ Ja, omfordel",type="primary",use_container_width=True,key="ja_reassign"):
                if not prefs_m: st.error("Ingen ønsker indsendt.")
                else:
                    data=auto_assign(data,mkey); save(data)
                    st.session_state.confirm_reassign=None
                    st.success("🎉 Vagter omfordelt!"); st.balloons(); st.rerun()
            if cb_.button("❌ Annuller",use_container_width=True,key="nej_reassign"):
                st.session_state.confirm_reassign=None; st.rerun()
    else:
        if st.button("🚀 Tildel vagter automatisk",type="primary",
                     use_container_width=True,key="tildel_btn"):
            if not prefs_m: st.error("Ingen frivillige har indsendt ønsker endnu.")
            else:
                data=auto_assign(data,mkey); save(data)
                st.success("🎉 Vagter er tildelt!"); st.balloons(); st.rerun()

    st.markdown("---")
    with st.expander("🛡️ Fail-safe: Download rådata"):
        st.caption("Hent alle indsendte ønsker som CSV — uanset om vagter er tildelt.")
        if prefs_m:
            rows=["Frivillig,Dato,Dag,Ønske"]
            for vid,prefs in prefs_m.items():
                navn=data["volunteers"].get(vid,{}).get("name",vid)
                for d_str,val in sorted(prefs.items()):
                    rows.append(f"{navn},{d_str},{DAG_LANG[date.fromisoformat(d_str).weekday()]},{val}")
            st.download_button("⬇️ Download ønsker (CSV)",
                               "\n".join(rows).encode("utf-8-sig"),
                               f"plexus_rawdata_{mkey}.csv","text/csv",
                               use_container_width=True,key="dl_rawdata")
        else:
            st.info("Ingen ønsker indsendt endnu.")

# ── Tab: Resultater ────────────────────────────────────────────────────────────
def _tab_resultater(data:dict):
    st.markdown("### 📊 Resultater")
    tildelte=sorted(data.get("assignments",{}).keys(),reverse=True)
    if not tildelte:
        st.info("📭 Ingen vagter er tildelt endnu."); return

    mkey=st.selectbox("Vælg måned",tildelte,format_func=mk_label,
                       key="resultater_month_select")
    asgn=data["assignments"][mkey]
    vols=data["volunteers"]
    st.caption(f"⏱️ Genereret: {asgn.get('generated_at','–')}")

    åbne   =len(asgn["open"])
    lukkede=len(asgn["closed"])
    aktivit=len(asgn.get("activity",[]))
    total  =åbne+lukkede
    pct    =round(100*åbne/total) if total>0 else 0

    c1,c2,c3,c4=st.columns(4)
    c1.metric("🟢 Åbne",åbne); c2.metric("🔵 Aktivitet",aktivit)
    c3.metric("🔴 Lukkede",lukkede); c4.metric("📈 Åbningspct.",f"{pct}%")

    if asgn.get("unmet_quota"):
        with st.expander("⚠️ Frivillige med ufyldt kvote"):
            for vid,mangler in asgn["unmet_quota"].items():
                st.write(f"• **{vols.get(vid,{}).get('name',vid)}** mangler {mangler} vagt(er)")

    st.markdown("### 📅 Kalender-oversigt")
    st.markdown(
        cal_html_resultater(mkey,asgn["shifts"],asgn["open"],asgn["closed"],
                             asgn.get("activity",[]),vols),
        unsafe_allow_html=True)

    with st.expander("👤 Oversigt per frivillig"):
        for vid,vol in sorted(vols.items(),key=lambda x:x[1]["name"]):
            if not vol.get("active"): continue
            mine   =sorted(d for d,vs in asgn["shifts"].items() if vid in vs)
            kraevet=vol.get("required_shifts",2)
            ikon   ="✅" if len(mine)>=kraevet else "⚠️"
            akt    =" 🔵" if vol.get("aktivitetsudvalg") else ""
            st.markdown(f"**{ikon} {vol['name']}{akt}** — {len(mine)}/{kraevet} vagter")
            for d in mine:
                typ="🔵" if d in asgn.get("activity",[]) else "🟢"
                st.write(f"  • {typ} {full_dato(d)}")
            if len(mine)<kraevet:
                st.caption(f"  Fik {kraevet-len(mine)} færre end aftalt.")

    rækker=["Dato,Dag,Status,Type,Frivillige"]
    for d in sorted(asgn["shifts"]):
        navne="; ".join(vols[v]["name"] for v in asgn["shifts"][d] if v in vols)
        status="Åben" if d in asgn["open"] else "Lukket"
        ttype ="Aktivitet" if d in asgn.get("activity",[]) else "Normal"
        rækker.append(f"{d},{DAG_LANG[date.fromisoformat(d).weekday()]},{status},{ttype},{navne}")

    st.download_button("⬇️ Download vagtplan (CSV)",
                       "\n".join(rækker).encode("utf-8-sig"),
                       f"plexus_vagtplan_{mkey}.csv","text/csv",
                       use_container_width=True,key="dl_vagtplan")

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
        side=st.radio("",["🙋 Frivillig","⚙️ Administrator"],
                      label_visibility="hidden",key="nav_side")
        st.divider()
        st.caption(f"Version {VERSION}")
        st.caption("Lavet af Fabian Salvatore")

    if side=="🙋 Frivillig":
        side_frivillig(data)
    else:
        side_admin(data)

if __name__=="__main__":
    main()

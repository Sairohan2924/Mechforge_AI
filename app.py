from __future__ import annotations

import json, os
from pathlib import Path

import pandas as pd
import streamlit as st
from datetime import datetime, timezone

APP_VERSION = '3.1.1'

def local_timestamp(value):
    """Convert SQLite's UTC CURRENT_TIMESTAMP text into the computer's local time."""
    if not value:
        return value
    try:
        text=str(value).strip()
        dt=datetime.fromisoformat(text.replace('Z','+00:00'))
        if dt.tzinfo is None:
            dt=dt.replace(tzinfo=timezone.utc)
        return dt.astimezone().strftime('%Y-%m-%d %H:%M:%S')
    except (TypeError, ValueError):
        return value

from database import (init_db, authenticate, create_user, ensure_demo_user, list_projects,
                      get_project, upsert_project, delete_project, save_analysis, list_analyses,
                      add_chat, get_chat, list_suppliers, upsert_supplier, save_quote, list_quotes)
from drawing_analyzer import analyze_drawing_text, extract_drawing_text
from dfm_engine import analyze_design, project_what_if, optimize_design, compare_processes, PROCESS_OPTIONS
from report import build_report
from drawing_annotation import annotate_drawing
from step_analyzer import analyze_cad_file
from ai_assistant import answer as ai_answer
from suppliers import quote_supplier
from email_service import send_email

st.set_page_config(page_title='MechForge AI', page_icon='⚙️', layout='wide', initial_sidebar_state='expanded')

st.markdown('''
<style>
.block-container{max-width:1500px;padding-top:1.1rem;padding-bottom:3rem}
section[data-testid="stSidebar"]{border-right:1px solid #263241}
section[data-testid="stSidebar"] .block-container{padding-top:1.4rem}
.mf-hero{padding:26px 30px;border:1px solid #2a3949;border-radius:20px;background:radial-gradient(circle at 85% 15%,rgba(43,139,216,.20),transparent 32%),linear-gradient(135deg,#0b1219,#111c28 60%,#0e1720);margin-bottom:22px;box-shadow:0 12px 35px rgba(0,0,0,.18)}
.mf-hero h1{margin:.45rem 0 .35rem;font-size:2.25rem;letter-spacing:-.04em}.mf-hero p{margin:0;color:#aebdcc;font-size:1rem}
.mf-badge{display:inline-block;padding:5px 11px;border-radius:999px;background:#102b40;border:1px solid #2b8bd8;color:#9edfff;font-size:.72rem;font-weight:800;letter-spacing:.08em}.mf-kicker{color:#8fa2b5;font-size:.78rem;font-weight:800;letter-spacing:.12em;text-transform:uppercase}.mf-title{font-size:2.45rem;font-weight:850;letter-spacing:-.045em;margin:.25rem 0}.mf-card h3{margin-top:0}.mf-navnote{font-size:.78rem;color:#7f91a3}.mf-status{display:inline-flex;align-items:center;gap:7px;padding:5px 9px;border-radius:999px;border:1px solid #30404f;background:#111b24;color:#b7c5d3;font-size:.75rem}.mf-dot{width:7px;height:7px;border-radius:50%;background:#38c98a;display:inline-block}.mf-auth{max-width:980px;margin:2.2rem auto 1rem}.mf-auth-panel{padding:26px 28px;border:1px solid #2b3744;border-radius:18px;background:linear-gradient(145deg,#111922,#0e151d);box-shadow:0 18px 50px rgba(0,0,0,.22)}
.mf-auth-panel h2{font-size:1.65rem;letter-spacing:-.025em;margin:.35rem 0 .25rem}.mf-auth-panel .mf-muted{font-size:.92rem;margin-bottom:1rem}.mf-auth-divider{display:flex;align-items:center;gap:12px;margin:1rem 0;color:#68798a;font-size:.72rem;text-transform:uppercase;letter-spacing:.12em}.mf-auth-divider:before,.mf-auth-divider:after{content:"";height:1px;background:#293642;flex:1}.mf-auth-foot{max-width:980px;margin:0 auto;text-align:center;color:#718193;font-size:.75rem}.mf-brand-mark{width:54px;height:54px;display:flex;align-items:center;justify-content:center;border-radius:16px;background:#102b40;border:1px solid #2b8bd8;font-size:1.8rem;box-shadow:0 8px 24px rgba(43,139,216,.14)}
.mf-section{font-size:1.15rem;font-weight:800;margin:1.1rem 0 .65rem}.mf-muted{color:#8d9bab}
.mf-card{padding:18px 20px;border:1px solid #2b3744;border-radius:16px;background:linear-gradient(145deg,#111922,#0f161e);box-shadow:0 8px 24px rgba(0,0,0,.12)}
.issue{padding:17px;border-radius:14px;margin:10px 0;border:1px solid #303b47;background:#121a23;color:#f0f2f6}.issue .small{color:#9eabb8;font-weight:700}
.success-card{padding:16px;border:1px solid #246b48;border-radius:14px;background:#0e241a}.warning-card{padding:16px;border:1px solid #765b1e;border-radius:14px;background:#251e0d}
[data-testid="stMetric"]{border:1px solid #293542;border-radius:14px;padding:12px 14px;background:#111922}
div[data-testid="stFileUploader"]{border:1px dashed #405364;border-radius:14px;padding:5px;background:#101820}
button[kind="primary"]{font-weight:750}
.mf-page-title{padding:4px 0 8px}.mf-page-title h2{font-size:2rem;margin:.15rem 0 .2rem;letter-spacing:-.03em}.mf-page-title p{margin:0;color:#93a2b1}.mf-kicker{font-size:.7rem;font-weight:850;letter-spacing:.13em;color:#6fcfff}.mf-muted{color:#93a2b1}
.mf-workflow{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:12px 0 24px}.mf-step{display:flex;align-items:center;gap:10px;padding:11px 13px;border:1px solid #273542;border-radius:12px;background:#101820;color:#8293a4;font-size:.82rem}.mf-step b{display:flex;width:25px;height:25px;align-items:center;justify-content:center;border-radius:50%;border:1px solid #334555;font-size:.68rem}.mf-step.active{border-color:#2b8bd8;color:#d9edf8;background:#102331}.mf-step.active b{border-color:#2b8bd8;color:#9edfff}.mf-section{font-size:1.15rem;font-weight:800;margin:1.1rem 0 .65rem;letter-spacing:-.015em}
@media(max-width:900px){.mf-workflow{grid-template-columns:repeat(2,1fr)}}
</style>
''', unsafe_allow_html=True)

init_db()

DEFAULTS={'wall':4.0,'radius':3.0,'pocket_depth':20.0,'pocket_width':12.0,'hole_dia':10.0,'hole_depth':20.0,'tolerance':0.050,'surface_ra':3.2}
for k,v in DEFAULTS.items():
    # Streamlit widget state can survive reruns/version changes. Normalize every
    # DFM input to a real float before number_input sees it; otherwise Streamlit
    # can raise MixedNumericTypesError when an old string value is in session state.
    raw=st.session_state.get(k,v)
    try:
        st.session_state[k]=float(raw)
    except (TypeError,ValueError):
        st.session_state[k]=float(v)
for k,v in {'analysis':None,'drawing_text':'','drawing_info':None,'uploaded_name':None,'optimization':None,'process_comparison':None,'annotated_drawing':None,'cad_info':None,'cad_name':None,'active_project_id':None,'material_choice':'Aluminium 6061','process_choice':'AUTO SELECT','project_name':'Demo Bracket','component_name':'CNC Machined Bracket','quantity_value':50,'nav':'New Analysis','pending_nav':None,'demo_mode':False,'demo_upload_used':False,'demo_upload_type':None}.items(): st.session_state.setdefault(k,v)

# ---------- Authentication ----------
def auth_screen():
    st.markdown(f"""<div class="mf-auth">
      <div class="mf-hero">
        <div style="display:flex;align-items:center;gap:16px">
          <div class="mf-brand-mark">⚙️</div>
          <div>
            <div class="mf-kicker">Engineering Intelligence Platform</div>
            <div class="mf-title">MechForge AI</div>
          </div>
        </div>
        <p style="margin-top:1rem">Design-for-manufacturing analysis, CAD geometry intelligence and production decision support in one workspace.</p>
      </div>
    </div>""", unsafe_allow_html=True)
    left,right=st.columns([1,1],gap='large')
    with left:
        with st.container(border=True):
            st.markdown('<div class="mf-kicker">Workspace access</div><h2>Sign in</h2><p class="mf-muted">Access your projects, analyses and engineering history.</p>',unsafe_allow_html=True)
            email=st.text_input('Email address', key='login_email', placeholder='you@company.com')
            password=st.text_input('Password', type='password', key='login_password', placeholder='Enter your password')
            if st.button('Sign in to workspace', type='primary', use_container_width=True):
                user=authenticate(email.strip(),password)
                if user:
                    st.session_state.user=user; st.session_state.demo_mode=False; st.rerun()
                else:
                    st.error('We could not sign you in. Check your email and password.')
            st.markdown('<div class="mf-auth-divider"><span>or</span></div>',unsafe_allow_html=True)
            if st.button('Continue with demo workspace', use_container_width=True):
                st.session_state.user={'id':0,'name':'MechForge Demo','email':'demo@mechforge.ai','demo':True}
                st.session_state.demo_mode=True
                st.rerun()
            st.caption('Demo access includes one engineering-file upload per browser session. Create an account for continued use.')
    with right:
        with st.container(border=True):
            st.markdown('<div class="mf-kicker">New workspace</div><h2>Create your account</h2><p class="mf-muted">Start a personal engineering workspace for MechForge AI.</p>',unsafe_allow_html=True)
            name=st.text_input('Full name', key='reg_name', placeholder='Your name')
            remail=st.text_input('Work or personal email', key='reg_email', placeholder='you@company.com')
            rpass=st.text_input('Password', type='password', key='reg_password', placeholder='At least 6 characters')
            if st.button('Create workspace', use_container_width=True):
                if len(rpass)<6:
                    st.error('Use at least 6 characters for the password.')
                elif not name.strip() or '@' not in remail or '.' not in remail.split('@')[-1]:
                    st.error('Enter a valid name and email address.')
                else:
                    uid,err=create_user(name.strip(),remail.strip().lower(),rpass)
                    if err: st.error(err)
                    else: st.success('Workspace created. You can sign in now.')
            st.markdown('<div class="mf-auth-divider"><span>Included</span></div><div class="mf-muted">DFM analysis • CAD geometry • AI assistant • reports • project history</div>',unsafe_allow_html=True)
    st.markdown('<div class="mf-auth-foot">Passwords are protected with salted PBKDF2 hashing. Keep API keys and deployment secrets out of source control.</div>',unsafe_allow_html=True)

if 'user' not in st.session_state:
    auth_screen(); st.stop()

user=st.session_state.user
is_demo=bool(st.session_state.get('demo_mode') and user.get('demo',False))
demo_locked=is_demo and bool(st.session_state.get('demo_upload_used'))

def demo_gate_notice():
    if not is_demo:
        return
    if demo_locked:
        st.error('Demo limit reached — your one free engineering-file upload has been used. Create an account to continue with new drawings and CAD models.')
        if st.button('Create account to continue', type='primary', use_container_width=True, key='demo_create_account'):
            st.session_state.pop('user',None)
            st.session_state.demo_mode=False
            st.rerun()
    else:
        st.info('Demo mode: upload **one PDF/image OR one STEP/STP/STL file**. After the first successful upload, new file uploads are locked until you create an account.')

# Navigation requested by a button is applied BEFORE the radio widget is instantiated.
# Streamlit forbids changing a widget's keyed session_state value after creation.
if st.session_state.get('pending_nav'):
    st.session_state.nav = st.session_state.pop('pending_nav')

# ---------- Helpers ----------
def project_data():
    return dict(project=project,component=component,material=material,process=process,quantity=int(quantity),
        wall=float(st.session_state.wall),radius=float(st.session_state.radius),pocket_depth=float(st.session_state.pocket_depth),
        pocket_width=float(st.session_state.pocket_width),hole_dia=float(st.session_state.hole_dia),hole_depth=float(st.session_state.hole_depth),
        tolerance=float(st.session_state.tolerance),surface_ra=float(st.session_state.surface_ra),
        uploaded_name=st.session_state.uploaded_name,drawing_text=st.session_state.drawing_text,
        detected=(st.session_state.drawing_info or {}).get('detected',{}),cad=st.session_state.cad_info or {})

def reset_analysis_state():
    st.session_state.analysis=None; st.session_state.optimization=None; st.session_state.process_comparison=None; st.session_state.annotated_drawing=None

def render_mesh(cad_info):
    mesh=cad_info.get('mesh',{}); vertices=mesh.get('vertices',[]); triangles=mesh.get('triangles',[])
    if not vertices or not triangles: return
    if len(triangles)>30000:
        step=max(1,len(triangles)//30000); triangles=triangles[::step]
    x=[p[0] for p in vertices]; y=[p[1] for p in vertices]; z=[p[2] for p in vertices]
    i=[t[0] for t in triangles]; j=[t[1] for t in triangles]; k=[t[2] for t in triangles]
    import plotly.graph_objects as go
    fig=go.Figure(data=[go.Mesh3d(x=x,y=y,z=z,i=i,j=j,k=k,opacity=.78,flatshading=True,hoverinfo='skip')])
    fig.update_layout(height=600,margin=dict(l=0,r=0,t=0,b=0),scene=dict(aspectmode='data',xaxis_title='X (mm)',yaxis_title='Y (mm)',zaxis_title='Z (mm)'),paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig,use_container_width=True,config={'displaylogo':False})

def load_project(pid):
    p=get_project(user['id'],pid)
    if not p:return
    st.session_state.active_project_id=pid
    st.session_state.material_choice=p['material']; st.session_state.process_choice=p['process']; st.session_state.project_name=p['name']; st.session_state.component_name=p['component']; st.session_state.quantity_value=int(p['quantity'])
    for k in DEFAULTS: st.session_state[k]=DEFAULTS[k]
    st.session_state.analysis=None

# ---------- Sidebar ----------
with st.sidebar:
    st.markdown('<div class="mf-kicker">Engineering workspace</div><h2 style="margin:.2rem 0 .1rem">⚙️ MechForge</h2>',unsafe_allow_html=True)
    st.markdown(f'<span class="mf-status"><span class="mf-dot"></span>{user["name"]}</span>',unsafe_allow_html=True)
    if is_demo:
        st.caption('🧪 One-upload demo • account required after trial')
    nav=st.radio('Workspace',['New Analysis','Dashboard','CAD Studio','AI Assistant','Suppliers','Reports & History','Settings'], key='nav')
    st.divider()
    projects=[] if is_demo else list_projects(user['id'])
    if projects:
        labels=['New project']+[f"{p['name']} (#{p['id']})" for p in projects]
        selected=st.selectbox('Project',labels,index=0)
        if selected!='New project':
            pid=int(selected.rsplit('#',1)[1].rstrip(')'))
            if st.button('Open selected project',use_container_width=True): load_project(pid); st.session_state.pending_nav='New Analysis'; st.rerun()
    if st.button('Sign out',use_container_width=True):
        st.session_state.pop('user',None); st.rerun()

# ---------- Header ----------
st.markdown(f'<div class="mf-hero"><span class="mf-badge">PROFESSIONAL BUILD • v{APP_VERSION}</span><div class="mf-title">⚙️ MechForge AI</div><p>Engineering intelligence for manufacturability — analyze drawings and CAD, identify DFM risks, optimize designs and make informed manufacturing decisions.</p></div>', unsafe_allow_html=True)

# ---------- New Analysis ----------
if nav=='New Analysis':
    st.markdown('<div class="mf-page-title"><div><div class="mf-kicker">DESIGN ASSESSMENT WORKSPACE</div><h2>New Analysis</h2><p>Build a traceable manufacturability assessment from drawing data, CAD geometry and engineering inputs.</p></div></div>',unsafe_allow_html=True)
    st.markdown('''<div class="mf-workflow"><div class="mf-step active"><b>01</b><span>Define component</span></div><div class="mf-step"><b>02</b><span>Load engineering data</span></div><div class="mf-step"><b>03</b><span>Verify inputs</span></div><div class="mf-step"><b>04</b><span>Run DFM</span></div></div>''',unsafe_allow_html=True)

    st.markdown('<div class="mf-section">01 · Component definition</div>',unsafe_allow_html=True)
    s1,s2,s3,s4=st.columns([1.35,1.35,1.1,1.25])
    with s1: project=st.text_input('Project name',key='project_name',placeholder='e.g. EV Battery Bracket')
    with s2: component=st.text_input('Component',key='component_name',placeholder='e.g. CNC Machined Bracket')
    materials=['Aluminium 6061','Aluminium 7075','Mild Steel','Stainless Steel','Cast Iron','Brass','Copper','Titanium','Engineering Plastic']
    # Apply detected drawing selections BEFORE the widgets are instantiated.
    # Streamlit forbids changing a widget's session_state key after that widget is created.
    if st.session_state.get('pending_material') in materials:
        st.session_state.material_choice = st.session_state.pop('pending_material')
    if st.session_state.get('pending_process') in PROCESS_OPTIONS:
        st.session_state.process_choice = st.session_state.pop('pending_process')
    with s3:
        material=st.selectbox('Material',materials,index=materials.index(st.session_state.material_choice) if st.session_state.material_choice in materials else 0,key='material_choice')
    with s4:
        process=st.selectbox('Manufacturing process',PROCESS_OPTIONS,index=PROCESS_OPTIONS.index(st.session_state.process_choice) if st.session_state.process_choice in PROCESS_OPTIONS else 0,key='process_choice')
    quantity=st.number_input('Production quantity',1,100000,key='quantity_value',step=1,help='Used for batch and per-unit cost estimation.')

    st.markdown('<div class="mf-section">02 · Engineering data</div>',unsafe_allow_html=True)
    demo_gate_notice()
    st.caption('Upload the source drawing and/or a CAD model. MechForge keeps extracted drawing values, CAD geometry and manual inputs distinguishable.')
    up1,up2=st.columns(2,gap='large')
    with up1:
        with st.container(border=True):
            st.markdown('**2D drawing**')
            st.caption('PDF, PNG or JPG · dimensions, tolerances, finish and manufacturing notes')
            uploaded=st.file_uploader('Upload drawing',type=['pdf','png','jpg','jpeg'],key='drawing_upload',label_visibility='collapsed',disabled=demo_locked or (is_demo and st.session_state.get('demo_upload_type')=='cad'))
    with up2:
        with st.container(border=True):
            st.markdown('**3D CAD model**')
            st.caption('STEP, STP or STL · geometry, topology and dimensional envelope')
            cad_uploaded=st.file_uploader('Upload CAD model',type=['step','stp','stl'],key='cad_upload',label_visibility='collapsed',disabled=demo_locked or (is_demo and st.session_state.get('demo_upload_type')=='drawing'))

    if uploaded is not None and uploaded.name!=st.session_state.uploaded_name and not demo_locked:
        text,method=extract_drawing_text(uploaded.name,uploaded.getvalue()); info=analyze_drawing_text(text)
        st.session_state.uploaded_name=uploaded.name; st.session_state.drawing_text=text; st.session_state.drawing_info=info
        reset_analysis_state()
        if is_demo:
            st.session_state.demo_upload_used=True; st.session_state.demo_upload_type='drawing'
        detected=info.get('detected',{})
        for key in DEFAULTS:
            if key in detected: st.session_state[key]=float(detected[key])
        dm=detected.get('material'); dp=detected.get('process')
        if dm in materials: st.session_state.pending_material=dm
        if dp in PROCESS_OPTIONS: st.session_state.pending_process=dp
        # Rerun so the detected selections are applied before the selectbox widgets are created.
        if dm in materials or dp in PROCESS_OPTIONS:
            st.rerun()
    if cad_uploaded is not None and cad_uploaded.name!=st.session_state.cad_name and not demo_locked and not (is_demo and st.session_state.get('demo_upload_used')):
        try:
            st.session_state.cad_info=analyze_cad_file(cad_uploaded.name,cad_uploaded.getvalue()); st.session_state.cad_name=cad_uploaded.name; reset_analysis_state()
            if is_demo:
                st.session_state.demo_upload_used=True; st.session_state.demo_upload_type='cad'
            st.success(f'CAD parsed successfully: {cad_uploaded.name}')
        except Exception as exc: st.error(f'CAD parsing failed: {exc}')

    if st.session_state.drawing_info:
        info=st.session_state.drawing_info; det=info.get('detected',{})
        st.success(f"Drawing loaded: {st.session_state.uploaded_name}")
        st.info(f"Extraction: {info.get('notes',[''])[0] if info.get('notes') else 'Detected drawing text.'} • Verify extracted values against the source drawing before manufacturing.")
        if det:
            cols=st.columns(4)
            labels=[('wall','Minimum wall','mm'),('radius','Minimum radius','mm'),('pocket_depth','Deepest pocket','mm'),('pocket_width','Narrowest pocket','mm'),('hole_dia','Hole diameter','mm'),('hole_depth','Deepest hole','mm'),('tolerance','Tightest tolerance ±','mm'),('surface_ra','Surface finish Ra','µm')]
            for n,(k,l,u) in enumerate(labels):
                if k in det: cols[n%4].metric(l,f"{det[k]:g} {u}")
            if det.get('dimensions'): st.write('**Linear dimensions:** '+', '.join(f'{x:g} mm' for x in det['dimensions'][:30]))
            st.write('**Detected feature notes:** '+ ' • '.join(info.get('features',[])) if info.get('features') else '')

    if st.session_state.cad_info:
        ci=st.session_state.cad_info
        st.subheader('CAD Geometry Intelligence')
        c=st.columns(6)
        c[0].metric('Format',ci['format']); c[1].metric('Solids',ci['solids']); c[2].metric('Faces',ci['faces']); c[3].metric('Edges',ci['edges']); c[4].metric('Volume',f"{ci['volume_mm3']:,.0f} mm³"); c[5].metric('Surface area',f"{ci['surface_area_mm2']:,.0f} mm²")
        b=ci['bbox']; st.write(f"**Bounding box:** {b['x']:.2f} × {b['y']:.2f} × {b['z']:.2f} mm")
        st.caption('STEP geometry is parsed with OCCT/CadQuery. CAD geometry does not replace drawing tolerances or functional requirements.')
        with st.expander('3D CAD Viewer',expanded=True): render_mesh(ci)

    st.markdown('<div class="mf-section">03 · Verify design inputs</div>',unsafe_allow_html=True)
    source_count=int(bool(st.session_state.drawing_info))+int(bool(st.session_state.cad_info))
    st.info(('Engineering sources loaded: **%d/2**. ' % source_count) + 'Values detected from drawings are pre-filled. Verify all critical dimensions against the source drawing before manufacturing.')
    cols=st.columns(4)
    specs=[('wall','Minimum wall thickness (mm)',0.1,100,0.1,'%.2f'),('radius','Minimum internal radius (mm)',0,50,0.5,'%.2f'),('pocket_depth','Deepest pocket (mm)',0,500,1,'%.2f'),('pocket_width','Narrowest pocket width (mm)',0.5,500,0.5,'%.2f'),('hole_dia','Typical hole diameter (mm)',0.5,200,0.5,'%.2f'),('hole_depth','Deepest hole (mm)',0,500,1,'%.2f'),('tolerance','Tightest tolerance ± (mm)',0.001,5,0.001,'%.3f'),('surface_ra','Surface roughness Ra (µm)',0.1,100,0.1,'%.1f')]
    for idx,(k,label,lo,hi,step,fmt) in enumerate(specs):
        # Keep value/min/max/step all as floats for Streamlit's numeric widget.
        current=float(st.session_state.get(k,lo))
        current=max(float(lo),min(float(hi),current))
        st.session_state[k]=current
        cols[idx%4].number_input(label,min_value=float(lo),max_value=float(hi),value=current,key=k,step=float(step),format=fmt)

    st.markdown('<div class="mf-section">04 · Manufacturing assessment</div>',unsafe_allow_html=True)
    st.caption('Run the deterministic DFM engine after reviewing the extracted and manually entered values.')
    if st.button('🔍 Run DFM Analysis',type='primary',use_container_width=True):
        data=project_data(); st.session_state.analysis=analyze_design(data); reset_analysis_state(); st.session_state.analysis=analyze_design(data)
        if is_demo:
            st.session_state.active_project_id=None
        else:
            pid=upsert_project(user['id'],project,component,material,process,int(quantity),st.session_state.active_project_id)
            st.session_state.active_project_id=pid
            save_analysis(user['id'],pid,project,st.session_state.analysis)

    a=st.session_state.analysis
    if a:
        st.divider(); st.header('DFM Analysis')
        top=st.columns(4); top[0].metric('Manufacturability',f"{a['score']}/100"); top[1].metric('Recommended Process',a['recommended_process']); top[2].metric('Estimated / unit',f"₹{a['unit_low']:,.0f}–₹{a['unit_high']:,.0f}"); top[3].metric('Machining Time',f"{a['minutes']:.1f} min")
        st.progress(a['score']/100); st.caption(f"Classification: **{a['classification']}**")
        left,right=st.columns([1.15,1])
        with left:
            st.subheader('Score Breakdown')
            for name,value in a['breakdown'].items(): st.write(f"**{name}** — {value}/100"); st.progress(value/100)
            st.subheader('Engineering Findings')
            for issue in a['issues']:
                icon={'HIGH':'🔴','MEDIUM':'🟡','GOOD':'🟢'}.get(issue['priority'],'ℹ️')
                st.markdown(f"<div class='issue'><b>{icon} {issue['priority']} — {issue['title']}</b><br><br><span class='small'>Observed:</span> {issue['observed']}<br><br><span class='small'>Problem:</span> {issue['problem']}<br><br><span class='small'>Recommendation:</span> {issue['recommendation']}<br><br><span class='small'>Manufacturing Benefit:</span> {issue['benefit']}</div>",unsafe_allow_html=True)
        with right:
            st.subheader('Process Recommendation'); st.write(f'### {a["recommended_process"]}'); st.write(f"Confidence: **{a['confidence']}%**")
            for r in a['reasons']: st.write('✓',r)
            st.write('**Alternative:**',a['alternative'])
            st.subheader('Cost Assumptions'); st.write(f"Quantity: **{quantity:,}**"); st.write(f"Estimated batch: **₹{a['batch_low']:,.0f}–₹{a['batch_high']:,.0f}**")
            st.caption('Illustrative estimate, not a supplier quotation.')
            st.subheader('Design What-If'); nr=st.slider('Change internal radius',0.,15.,float(st.session_state.radius),.5); st.write(f'Projected DFM score: **{project_what_if(a,nr)}/100**')

        st.divider(); st.header('🖍️ Drawing Issue Annotation')
        if uploaded:
            if st.button('🖍️ Generate Annotated Drawing',use_container_width=True):
                try:
                    issues=[x for x in a.get('issues',[]) if x.get('priority') in {'HIGH','MEDIUM'}]; bb,ext=annotate_drawing(uploaded.name,uploaded.getvalue(),issues); st.session_state.annotated_drawing={'bytes':bb,'ext':ext,'name':uploaded.name}
                except Exception as exc: st.error(str(exc))
            if st.session_state.annotated_drawing:
                ad=st.session_state.annotated_drawing; st.success('Annotated drawing generated successfully.'); st.download_button('⬇️ Download Annotated Drawing',ad['bytes'],f"{ad['name'].rsplit('.',1)[0]}_MechForge_Annotated.{ad['ext']}",'application/pdf' if ad['ext']=='pdf' else 'image/png',use_container_width=True)

        st.divider(); st.header('🛠️ Optimize My Design')
        if st.button('✨ Generate Optimization Plan',use_container_width=True): st.session_state.optimization=optimize_design(project_data())
        opt=st.session_state.optimization
        if opt:
            o=opt['original']; z=opt['optimized']; st.subheader('Optimization Result — Before → Optimized')
            q=st.columns(4); q[0].metric('DFM Score',f"{z['score']}/100",f"Before {o['score']}/100 • {opt['score_gain']:+d}"); q[1].metric('Estimated / unit',f"₹{z['unit_low']:,.0f}–₹{z['unit_high']:,.0f}",f"Before ₹{o['unit_low']:,.0f}–₹{o['unit_high']:,.0f}"); q[2].metric('Machining Time',f"{z['minutes']:.1f} min",f"Before {o['minutes']:.1f} min • {z['minutes']-o['minutes']:+.1f}"); q[3].metric('Classification',z['classification'],f"Before {o['classification']}")
            st.success(f"Optimization found {len(opt['changes'])} cumulative change(s): {o['score']} → {z['score']}." if opt['improved'] else 'No score-improving change was identified.')
            for ch in opt['changes']: st.markdown(f"**{ch['parameter'].replace('_',' ').title()}:** `{ch['current']:g}` → `{ch['proposed']:g}`  \nReason: {ch['reason']}  \nBenefit: {ch['benefit']}")

        st.divider(); st.header('🏭 Manufacturing Process Comparison')
        if st.button('⚙️ Compare Manufacturing Processes',use_container_width=True): st.session_state.process_comparison=compare_processes(project_data())
        comp=st.session_state.process_comparison
        if comp:
            best=comp[0]; st.success(f"Recommended comparison winner: **{best['process']}** — {best['score']}/100 ({best['suitability']}).")
            st.dataframe(pd.DataFrame([{'Process':r['process'],'DFM / Suitability':f"{r['score']}/100",'Estimated / unit':f"₹{r['unit_low']:,.0f}–₹{r['unit_high']:,.0f}",'Estimated Time':f"{r['minutes']:.1f} min",'Suitability':r['suitability']} for r in comp]),use_container_width=True,hide_index=True)
            sel=st.selectbox('Inspect a process',[r['process'] for r in comp]); row=next(r for r in comp if r['process']==sel); d1,d2,d3=st.columns(3); d1.metric('DFM Suitability',f"{row['score']}/100"); d2.metric('Estimated / unit',f"₹{row['unit_low']:,.0f}–₹{row['unit_high']:,.0f}"); d3.metric('Estimated Time',f"{row['minutes']:.1f} min")
            l,r=st.columns(2)
            l.markdown('**Why it may fit**')
            for reason in (row.get('reasons') or []):
                if reason is not None and str(reason).strip():
                    l.write('✓ ' + str(reason))
            r.markdown('**Risks / limitations**')
            for risk in (row.get('risks') or []):
                if risk is not None and str(risk).strip():
                    r.write('⚠️ ' + str(risk))

        st.divider(); st.subheader('DFM Report & Email')
        report_bytes=build_report(a); st.download_button('📄 Download DFM Report',report_bytes,'mechforge_dfm_report.html','text/html',use_container_width=True)
        with st.expander('Email this report'):
            to=st.text_input('Recipient email',value=user['email'])
            if st.button('Send report by email'):
                try: send_email(to,'MechForge AI DFM Report',report_bytes.decode('utf-8'),report_bytes,'mechforge_dfm_report.html'); st.success('Report emailed successfully.')
                except Exception as exc: st.error(f'Email failed: {exc}')

# ---------- Dashboard ----------
elif nav=='Dashboard':
    st.markdown('<div class="mf-page-title"><div><div class="mf-kicker">ENGINEERING COMMAND CENTER</div><h2>Dashboard</h2><p>Monitor manufacturability, project activity and production decisions from one workspace.</p></div></div>',unsafe_allow_html=True)
    projects=[] if is_demo else list_projects(user['id']); analyses=[] if is_demo else list_analyses(user['id']); quotes=[] if is_demo else list_quotes(user['id'])
    cloud_ai=bool(os.getenv('OPENAI_API_KEY'))
    scores=[x['payload'].get('score') for x in analyses if isinstance(x.get('payload',{}).get('score'),(int,float))]
    avg=(sum(scores)/len(scores)) if scores else 0
    high=sum(1 for x in analyses for i in x['payload'].get('issues',[]) if i.get('priority')=='HIGH')
    medium=sum(1 for x in analyses for i in x['payload'].get('issues',[]) if i.get('priority')=='MEDIUM')
    excellent=sum(1 for x in analyses if x['payload'].get('classification')=='Excellent')
    good=sum(1 for x in analyses if x['payload'].get('classification')=='Good')
    difficult=sum(1 for x in analyses if x['payload'].get('classification')=='Difficult')

    k=st.columns(4)
    k[0].metric('Projects',len(projects),help='Saved engineering projects in this workspace.')
    k[1].metric('Analyses',len(analyses),help='Completed DFM assessments saved to this account.')
    k[2].metric('Average DFM score',f'{avg:.0f}/100' if scores else '—',help='Average manufacturability score across saved analyses.')
    k[3].metric('High-priority findings',high,help='Total HIGH-priority DFM findings across saved analyses.')

    if not analyses:
        st.info('No analyses yet. Start a New Analysis to populate your engineering dashboard.')
    else:
        left,right=st.columns([1.25,.75])
        with left:
            st.markdown('<div class="mf-section">Manufacturability overview</div>',unsafe_allow_html=True)
            import plotly.graph_objects as go
            ordered=list(reversed(analyses[:20]))
            xs=[local_timestamp(x['created_at']) for x in ordered]
            ys=[x['payload'].get('score',0) for x in ordered]
            fig=go.Figure()
            fig.add_trace(go.Scatter(x=xs,y=ys,mode='lines+markers',name='DFM score',line=dict(width=3),marker=dict(size=7)))
            fig.add_hline(y=75,line_dash='dash',annotation_text='Good threshold',annotation_position='top left')
            fig.add_hline(y=90,line_dash='dot',annotation_text='Excellent threshold',annotation_position='top left')
            fig.update_yaxes(range=[0,100],title='Score / 100',gridcolor='rgba(120,140,160,.12)')
            fig.update_xaxes(title='Assessment time',gridcolor='rgba(120,140,160,.08)')
            fig.update_layout(height=330,margin=dict(l=10,r=10,t=15,b=10),paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',showlegend=False)
            st.plotly_chart(fig,use_container_width=True,config={'displaylogo':False})
        with right:
            st.markdown('<div class="mf-section">Assessment status</div>',unsafe_allow_html=True)
            status_df=pd.DataFrame({'Classification':['Excellent','Good','Needs Improvement','Difficult'],'Analyses':[excellent,good,sum(1 for x in analyses if x['payload'].get('classification')=='Needs Improvement'),difficult]})
            fig2=go.Figure(go.Bar(x=status_df['Analyses'],y=status_df['Classification'],orientation='h',text=status_df['Analyses'],textposition='auto'))
            fig2.update_layout(height=330,margin=dict(l=10,r=10,t=15,b=10),paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',xaxis_title='Analyses',yaxis=dict(autorange='reversed'))
            st.plotly_chart(fig2,use_container_width=True,config={'displaylogo':False})

        st.markdown('<div class="mf-section">Workspace health</div>',unsafe_allow_html=True)
        h=st.columns(4)
        h[0].metric('Excellent designs',excellent)
        h[1].metric('Good designs',good)
        h[2].metric('Medium findings',medium)
        h[3].metric('AI mode','Cloud AI' if cloud_ai else 'Local fallback')

        st.markdown('<div class="mf-section">Recent analyses</div>',unsafe_allow_html=True)
        rows=[]
        for x in analyses[:20]:
            p=x['payload']
            rows.append({'Date':local_timestamp(x['created_at']),'Project':x['name'] or 'Untitled','Component':p.get('component') or '—','DFM Score':p.get('score'),'Classification':p.get('classification'),'Process':p.get('recommended_process'),'Cost / unit':f"₹{p.get('unit_low',0):,.0f}–₹{p.get('unit_high',0):,.0f}"})
        st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True,column_config={'DFM Score':st.column_config.NumberColumn('DFM Score',format='%d/100')})

        st.markdown('<div class="mf-section">Projects</div>',unsafe_allow_html=True)
        if projects:
            for p in projects[:8]:
                proj_analyses=[a for a in analyses if a.get('project_id')==p['id']]
                latest=proj_analyses[0]['payload'] if proj_analyses else None
                score=latest.get('score') if latest else None
                with st.container(border=True):
                    a,b,c,d=st.columns([2.2,1.1,1.1,1.1])
                    a.markdown(f"**{p['name']}**  \n<span class='mf-muted'>{p['component']} • {p['material']}</span>",unsafe_allow_html=True)
                    b.metric('Latest DFM',f'{score}/100' if score is not None else '—')
                    c.metric('Quantity',p['quantity'])
                    if d.button('Open project',key=f"dash_open_{p['id']}",use_container_width=True):
                        load_project(p['id']); st.session_state.pending_nav='New Analysis'; st.rerun()
        else:
            st.info('No saved projects yet. Run a DFM analysis to create your first project.')

        with st.expander('Dashboard notes & data scope'):
            st.write('Scores and findings come from the saved deterministic DFM analyses. Cost figures are internal estimates, not live supplier quotations. CAD metrics are geometry-level measurements.')

# ---------- CAD Studio ----------

elif nav=='CAD Studio':
    st.markdown('<div class="mf-page-title"><div><div class="mf-kicker">CAD INSPECTION WORKSPACE</div><h2>CAD Studio</h2><p>Inspect STEP/STP and STL geometry, review measurable CAD properties and prepare the model for manufacturability assessment.</p></div></div>',unsafe_allow_html=True)
    st.markdown('<div class="mf-workflow"><div class="mf-step active"><b>01</b><span>Load CAD</span></div><div class="mf-step"><b>02</b><span>Inspect geometry</span></div><div class="mf-step"><b>03</b><span>Review metrics</span></div><div class="mf-step"><b>04</b><span>Use in analysis</span></div></div>',unsafe_allow_html=True)
    st.markdown('<div class="mf-section">01 · CAD model</div>',unsafe_allow_html=True)
    left,right=st.columns([1.05,1.95],gap='large')
    with left:
        with st.container(border=True):
            st.markdown('**Upload model**')
            if is_demo:
                demo_gate_notice()
            st.caption('Supported formats: STEP, STP and STL. Geometry is analyzed locally by the CAD parser.')
            cad=st.file_uploader('CAD model',type=['step','stp','stl'],key='cad_studio_upload',label_visibility='collapsed',disabled=demo_locked)
            if st.session_state.cad_name:
                st.caption(f"Current model: **{st.session_state.cad_name}**")
            st.info('Geometry-level analysis does not infer functional intent, GD&T, datum schemes or manufacturing notes that are not encoded in the model.')
    if cad and not demo_locked:
        try:
            with st.spinner('Analyzing CAD geometry…'):
                ci=analyze_cad_file(cad.name,cad.getvalue())
            st.session_state.cad_info=ci; st.session_state.cad_name=cad.name
            if is_demo:
                st.session_state.demo_upload_used=True; st.session_state.demo_upload_type='cad'
        except Exception as exc:
            st.error(f'Could not parse model: {exc}')
            ci=None
    else:
        ci=st.session_state.cad_info
    with right:
        with st.container(border=True):
            if ci:
                st.markdown('**Interactive model inspection**')
                render_mesh(ci)
            else:
                st.markdown('### CAD preview')
                st.info('Upload a STEP/STP or STL model to activate the interactive 3D inspection view.')
    if ci:
        st.markdown('<div class="mf-section">02 · Geometry summary</div>',unsafe_allow_html=True)
        c=st.columns(6)
        c[0].metric('Format',ci['format'])
        c[1].metric('Solids',ci['solids'])
        c[2].metric('Faces',ci['faces'])
        c[3].metric('Edges',ci['edges'])
        c[4].metric('Volume',f"{ci['volume_mm3']:,.0f} mm³")
        c[5].metric('Surface area',f"{ci['surface_area_mm2']:,.0f} mm²")
        b=ci['bbox']
        st.markdown(f'<div class="mf-card"><b>Bounding box</b><br><span class="mf-muted">X × Y × Z</span><br><strong>{b['x']:.2f} × {b['y']:.2f} × {b['z']:.2f} mm</strong></div>',unsafe_allow_html=True)
        st.markdown('<div class="mf-section">03 · Geometry intelligence</div>',unsafe_allow_html=True)
        d=ci.get('derived',{}) or {}
        dc=st.columns(3)
        dc[0].metric('Aspect ratio',f"{d.get('aspect_ratio',0):.2f}")
        dc[1].metric('Complexity',f"{d.get('face_edge_complexity',0):.2f}")
        dc[2].metric('Compactness',f"{d.get('compactness',0):.3f}")
        st.caption('These indicators describe geometric complexity; they are not a substitute for feature-level manufacturing validation.')
        with st.expander('Technical CAD report'):
            st.json({k:v for k,v in ci.items() if k!='mesh'})
        st.markdown('<div class="mf-section">04 · Next engineering action</div>',unsafe_allow_html=True)
        st.success('CAD geometry is loaded. For a complete manufacturability assessment, combine this model with the engineering drawing and verified DFM inputs in New Analysis.')
        if st.button('Open New Analysis',type='primary',use_container_width=True):
            st.session_state.pending_nav='New Analysis'; st.rerun()

# ---------- AI Assistant ----------
elif nav=='AI Assistant':
    if is_demo:
        st.info('Demo mode includes one file upload for evaluation. Create an account to keep project history and continue using the full workspace.')
    st.markdown('<div class="mf-page-title"><div><div class="mf-kicker">MECHFORGE COPILOT</div><h2>AI Engineering Assistant</h2><p>General-purpose AI with project-aware engineering context when available.</p></div></div>',unsafe_allow_html=True)
    a=st.session_state.analysis or {}; c=st.session_state.cad_info or {}; pid=st.session_state.active_project_id
    key_configured=bool(os.getenv('OPENAI_API_KEY'))
    if not key_configured:
        try: key_configured=bool(st.secrets['OPENAI_API_KEY'])
        except Exception: pass
    mode_label='Cloud AI connected' if key_configured else 'Local fallback'
    st.markdown(f'<div class="mf-card"><b>Assistant status</b><br><span class="mf-muted">● {mode_label}</span> &nbsp; <span class="mf-muted">Project context: {"available" if (a or c) else "not loaded"}</span></div>',unsafe_allow_html=True)
    st.write('')
    if pid:
        history=get_chat(user['id'],pid)
        if history:
            with st.expander('Conversation history',expanded=True):
                for msg in history[-12:]:
                    with st.chat_message('user' if msg['role']=='user' else 'assistant'):
                        st.write(msg['content'])
        else:
            st.info('Start a conversation. Ask about this design or any engineering/general topic.')
    else:
        history=[]
        st.info('No project is selected. You can still ask general questions. Select or create a project when you want project-specific context.')
    suggestions=['Explain my DFM score','How can I reduce machining cost?','What is GD&T?','Compare 6061 vs 7075','Give me CNC interview questions']
    st.markdown('**Try a prompt**')
    pc=st.columns(len(suggestions))
    for i,prompt in enumerate(suggestions):
        if pc[i].button(prompt,key=f'ai_suggest_{i}',use_container_width=True):
            st.session_state.ai_prefill=prompt; st.rerun()
    q=st.chat_input('Ask anything about engineering, CAD, manufacturing, Python, or general knowledge…')
    if st.session_state.get('ai_prefill'):
        q=st.session_state.pop('ai_prefill')
    if q:
        if not is_demo:
            add_chat(user['id'],pid,'user',q)
        with st.spinner('MechForge AI is thinking…'):
            reply,mode=ai_answer(q,a,c,history)
        if not is_demo:
            add_chat(user['id'],pid,'assistant',reply)
        with st.chat_message('user'): st.write(q)
        with st.chat_message('assistant'): st.write(reply)
        st.caption(f'Assistant mode: {mode}')

# ---------- Suppliers ----------
elif nav=='Suppliers':
    if is_demo:
        st.info('Supplier management and saved quotations are available after account creation.')
    st.markdown('<div class="mf-page-title"><div><div class="mf-kicker">PROCUREMENT WORKSPACE</div><h2>Suppliers & Quotes</h2><p>Manage internal supplier profiles and compare transparent manufacturing estimates.</p></div></div>',unsafe_allow_html=True)
    st.warning('Supplier pricing is an internal estimate model, not a live marketplace or binding quotation.')
    suppliers=[] if is_demo else list_suppliers(user['id'])
    m1,m2,m3,m4=st.columns(4)
    m1.metric('Suppliers',len(suppliers)); m2.metric('Projects',len(list_projects(user['id']))); m3.metric('Saved quotes',len(list_quotes(user['id']))); m4.metric('Active analysis','Yes' if st.session_state.analysis else 'No')
    st.markdown('<div class="mf-section">Supplier directory</div>',unsafe_allow_html=True)
    with st.expander('＋ Add supplier',expanded=not bool(suppliers)):
        if is_demo:
            st.caption('🔒 Account required to save supplier profiles and quotations.')
        c=st.columns(2)
        name=c[0].text_input('Supplier name',placeholder='Example Manufacturing Co.')
        loc=c[1].text_input('Location',placeholder='Hyderabad, Telangana')
        procs=st.text_input('Supported processes',placeholder='CNC Milling, CNC Turning, Grinding')
        c=st.columns(4)
        rate=c[0].number_input('Machine rate ₹/h',100.,10000.,900.,step=50.)
        setup=c[1].number_input('Setup cost ₹',0.,100000.,1500.,step=100.)
        mf=c[2].number_input('Material factor',0.2,5.,1.0,step=0.1)
        lead=c[3].number_input('Lead time (days)',1,365,7,step=1)
        email=st.text_input('Supplier email (optional)')
        if st.button('Save supplier profile',type='primary',disabled=is_demo):
            if name.strip():
                if not is_demo:
                    upsert_supplier(user['id'],{'name':name,'location':loc,'processes':procs,'machine_rate':rate,'setup_cost':setup,'material_factor':mf,'lead_days':lead,'email':email})
                st.success('Supplier profile saved.'); st.rerun()
            else: st.error('Supplier name is required.')
    if suppliers:
        for s in suppliers:
            with st.container(border=True):
                a1,a2,a3=st.columns([2.2,3,2])
                a1.markdown(f"**{s['name']}**\n\n{s.get('location') or 'Location not specified'}")
                a2.markdown(f"**Processes**\n\n{s.get('processes') or 'Not specified'}")
                a3.markdown(f"**₹{float(s.get('machine_rate',0)):,.0f}/h** machine rate\n\nLead time: **{int(s.get('lead_days',0))} days**")
    a=st.session_state.analysis
    if a and suppliers:
        st.markdown('<div class="mf-section">Quote comparison</div>',unsafe_allow_html=True)
        quote_qty=int(st.session_state.get('quantity_value',50)); rows=[quote_supplier(s,a,quote_qty) for s in suppliers]
        qdf=pd.DataFrame(rows).sort_values('unit_cost')
        st.dataframe(qdf,use_container_width=True,hide_index=True,column_config={'unit_cost':st.column_config.NumberColumn('Unit cost',format='₹%.0f'),'total_cost':st.column_config.NumberColumn('Batch total',format='₹%.0f')})
        best=qdf.iloc[0]
        st.success(f"Lowest modeled unit cost: **₹{best['unit_cost']:,.0f}** from **{best['supplier']}**. Validate with an actual supplier quote.")
        chosen=st.selectbox('Save comparison result for supplier',[r['supplier'] for r in rows])
        qr=next(r for r in rows if r['supplier']==chosen)
        if st.button('Save selected quote',type='primary',disabled=is_demo):
            sid=next(s['id'] for s in suppliers if s['name']==chosen)
            if not is_demo:
                save_quote(user['id'],st.session_state.active_project_id, sid,quote_qty,qr['unit_cost'],qr['total_cost'],qr['lead_days'],qr['notes']); st.success('Quote saved to history.'); st.rerun()
    elif not a: st.info('Run a DFM analysis to unlock project-specific quote comparison.')
    qrows=list_quotes(user['id'])
    if qrows:
        st.markdown('<div class="mf-section">Quote history</div>',unsafe_allow_html=True)
        qdf=pd.DataFrame(qrows)[['created_at','project_name','supplier_name','quantity','unit_cost','total_cost','lead_days']].copy(); qdf['created_at']=qdf['created_at'].map(local_timestamp)
        st.dataframe(qdf,use_container_width=True,hide_index=True,column_config={'unit_cost':st.column_config.NumberColumn('Unit cost',format='₹%.0f'),'total_cost':st.column_config.NumberColumn('Total',format='₹%.0f')})

# ---------- Reports & History ----------
elif nav=='Reports & History':
    if is_demo:
        st.info('Saved reports and analysis history require an account. Your current demo result remains available in this session.')
    st.markdown('<div class="mf-page-title"><div><div class="mf-kicker">DOCUMENT CONTROL</div><h2>Reports & History</h2><p>Review, load and export previous engineering assessments.</p></div></div>',unsafe_allow_html=True)
    rows=[] if is_demo else list_analyses(user['id'])
    projects=[] if is_demo else list_projects(user['id'])
    r1,r2,r3,r4=st.columns(4)
    r1.metric('Analyses',len(rows)); r2.metric('Projects',len(projects)); r3.metric('Excellent',sum(x['payload'].get('classification')=='Excellent' for x in rows)); r4.metric('High-risk',sum(any(i.get('priority')=='HIGH' for i in x['payload'].get('issues',[])) for x in rows))
    if rows:
        search=st.text_input('Search history',placeholder='Project, component or process…')
        filtered=[x for x in rows if not search.strip() or search.lower() in (x['name']+' '+x['payload'].get('component','')+' '+x['payload'].get('recommended_process','')).lower()]
        for x in filtered:
            p=x['payload']; score=p.get('score','—'); classification=p.get('classification','—')
            with st.container(border=True):
                c1,c2,c3,c4=st.columns([2.2,1,1.6,1.5])
                c1.markdown(f"**{x['name']}**\n\n{p.get('component','—')}")
                c2.metric('DFM',f"{score}/100")
                c3.markdown(f"**Process**\n{p.get('recommended_process','—')}\n\n**Status**\n{classification}")
                c4.caption(local_timestamp(x['created_at']))
                b1,b2=st.columns(2)
                if b1.button('Load analysis',key=f'load_hist_{x["id"]}',use_container_width=True):
                    st.session_state.analysis=p; st.session_state.pending_nav='New Analysis'; st.rerun()
                if b2.download_button('Download report',data=build_report(p),file_name=f"MechForge_{x['id']}_DFM_Report.html",mime='text/html',key=f'dl_hist_{x["id"]}',use_container_width=True): pass
        if not filtered: st.info('No analyses match your search.')
    else:
        st.markdown('<div class="mf-card"><b>No assessments yet</b><br><span class="mf-muted">Run your first DFM analysis and it will appear here for revision and reporting.</span></div>',unsafe_allow_html=True)

# ---------- Settings ----------
elif nav=='Settings':
    if is_demo:
        st.info('Demo workspace. Create an account to unlock persistent projects, reports, suppliers and full workspace history.')
    st.markdown('<div class="mf-page-title"><div><div class="mf-kicker">SYSTEM CONFIGURATION</div><h2>Settings</h2><p>Configure AI, email, data storage and workspace preferences.</p></div></div>',unsafe_allow_html=True)
    tab1,tab2,tab3,tab4=st.tabs(['AI','Email','Data & Storage','Security'])
    with tab1:
        st.markdown('<div class="mf-section">AI configuration</div>',unsafe_allow_html=True)
        key_configured=bool(os.getenv('OPENAI_API_KEY'))
        if not key_configured:
            try: key_configured=bool(st.secrets['OPENAI_API_KEY'])
            except Exception: pass
        st.metric('AI connection','Connected' if key_configured else 'Local fallback')
        st.code('OPENAI_API_KEY = "your-key"\nMECHFORGE_AI_MODEL = "gpt-5.6-luna"',language='toml')
        st.caption('Keep API keys in environment variables or Streamlit Secrets. Never commit them to GitHub.')
    with tab2:
        st.markdown('<div class="mf-section">Email reports</div>',unsafe_allow_html=True)
        st.metric('SMTP status','Configured' if os.getenv('SMTP_HOST') else 'Not configured')
        st.code('SMTP_HOST=smtp.example.com\nSMTP_PORT=587\nSMTP_USER=...\nSMTP_PASSWORD=...\nSMTP_FROM=...',language='text')
        st.caption('SMTP is optional. It enables emailing generated engineering reports.')
    with tab3:
        st.markdown('<div class="mf-section">Workspace data</div>',unsafe_allow_html=True)
        st.write(f"Database path: `{os.getenv('MECHFORGE_DB','mechforge.db')}`")
        st.write(f"Projects: **{len(list_projects(user['id']))}**  ·  Analyses: **{len(list_analyses(user['id']))}**  ·  Suppliers: **{len(list_suppliers(user['id']))}**")
        st.info('SQLite is suitable for local development. For public production, move persistent user/project data to a managed database such as PostgreSQL.')
    with tab4:
        st.markdown('<div class="mf-section">Security posture</div>',unsafe_allow_html=True)
        st.success('Password storage uses salted PBKDF2-SHA256 hashing.')
        st.warning('Before public launch, add production session controls, password recovery, rate limiting, secure file validation, audit logging and managed database infrastructure.')
        st.caption(f"Signed in as {user['email']}")

st.divider(); st.caption('MechForge AI is an engineering decision-support prototype. CAD geometry, DFM rules, AI suggestions and supplier estimates must be validated by a qualified engineer and supplier before production.')

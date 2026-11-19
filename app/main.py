import os,json,secrets,re,csv,io
from contextlib import asynccontextmanager
from datetime import datetime,timezone,timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from fastapi import FastAPI,Request,Response,Depends,HTTPException
from fastapi.responses import FileResponse,StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func
from .db import init_db,session_scope
from .models import User,AuthSession,LoginAttempt,MonitoringTask,GlucoseReading,MedicationDose,PushSubscription,AgentRun,AgentStep
from .security import make_password_hash,verify_password,create_session,session_for_request,require_auth,require_csrf,digest,secure_cookie
from .services import (seed_user_plan,update_reminder_times,validate_clock,validate_reading,compute_summary,reading_csv,eligible_recipes,OCCASIONS,LABELS)
from .agents import run_insight_agents
from .notifications import email_ready,webpush_ready,dispatch_due,send_email,send_push

STATIC=Path(__file__).resolve().parent.parent/'static'
@asynccontextmanager
async def lifespan(app):
    init_db()
    yield
app=FastAPI(title='GlucoDiary AI',version='1.0.0',lifespan=lifespan,docs_url=None,redoc_url=None)

@app.middleware('http')
async def add_headers(request,call_next):
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='no-referrer'
    response.headers['X-Frame-Options']='DENY'
    response.headers['Permissions-Policy']='geolocation=(), camera=(), microphone=()'
    if request.url.path.startswith('/api/') or request.url.path.startswith('/internal/'):
        response.headers['Cache-Control']='no-store'
    return response

class LoginIn(BaseModel):
    email:str
    password:str
class ReadIn(BaseModel):
    value:float
    unit:str='mmol/L'
    occasion:str
    measured_at:str
    note:str=''
class SettingsIn(BaseModel):
    breakfast_time:str
    lunch_time:str
    dinner_time:str
    sleep_time:str
    email_enabled:bool=False
    push_enabled:bool=False
    alerts_confirmed:bool=False
class FoodIn(BaseModel):
    allergies_confirmed:bool=False
    enabled:bool=False
    cuisine:str='Indian'
    allergens:list[str]=Field(default_factory=list)
    avoid:list[str]=Field(default_factory=list)
class PushIn(BaseModel):
    endpoint:str
    keys:dict
class DoseIn(BaseModel):
    status:str
class ConsentIn(BaseModel):
    enabled:bool
class PasswordIn(BaseModel):
    current_password:str
    new_password:str

def auth(request:Request,db:Session=Depends(session_scope)):
    user,sess=require_auth(db,request)
    return db,user,sess

def mutation(request:Request,context=Depends(auth)):
    db,user,sess=context
    require_csrf(request,sess)
    return db,user,sess

def user_public(user):
    return {'email':user.email,'timezone':user.timezone,'alerts_confirmed':user.alerts_confirmed,'email_enabled':user.email_enabled,'push_enabled':user.push_enabled,'ai_consent':user.ai_consent,'food_enabled':user.food_enabled,'cuisine':user.cuisine,'allergens':json.loads(user.allergens or '[]'),'avoid':json.loads(user.avoid_ingredients or '[]'),'times':{'before_breakfast':user.breakfast_time,'before_lunch':user.lunch_time,'before_dinner':user.dinner_time,'before_sleep':user.sleep_time}}

@app.get('/')
def homepage():return FileResponse(STATIC/'index.html',headers={'Cache-Control':'no-store'})
@app.get('/demo')
def public_demo():return FileResponse(STATIC/'demo.html')
@app.get('/demo.js')
def demo_js():return FileResponse(STATIC/'demo.js',media_type='application/javascript')

@app.get('/app.js')
def js():return FileResponse(STATIC/'app.js',media_type='application/javascript')
@app.get('/style.css')
def css():return FileResponse(STATIC/'style.css',media_type='text/css')
@app.get('/manifest.webmanifest')
def manifest():return FileResponse(STATIC/'manifest.webmanifest',media_type='application/manifest+json')
@app.get('/sw.js')
def sw():return FileResponse(STATIC/'sw.js',media_type='application/javascript',headers={'Service-Worker-Allowed':'/'})
@app.get('/icon.svg')
def ico():return FileResponse(STATIC/'icon.svg',media_type='image/svg+xml')
@app.get('/healthz')
def health():return {'status':'ok','version':'1.0.0'}

@app.get('/api/setup/status')
def setup_status(db:Session=Depends(session_scope)):
    # Does not expose email addresses or server secrets.
    return {'needs_setup':db.query(User.id).first() is None and bool(os.getenv('BOOTSTRAP_TOKEN'))}

class BootstrapIn(BaseModel):
    setup_token:str
    email:str
    password:str

@app.post('/api/setup')
def bootstrap_remote(data:BootstrapIn,request:Request,response:Response,db:Session=Depends(session_scope)):
    import hmac
    secret=os.getenv('BOOTSTRAP_TOKEN','')
    if not secret or not hmac.compare_digest(secret,data.setup_token):raise HTTPException(403,'Invalid setup token')
    if db.query(User.id).first():raise HTTPException(409,'Application already initialised')
    email=data.email.strip().lower()
    if not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+',email):raise HTTPException(422,'Invalid email')
    try:pwh=make_password_hash(data.password)
    except ValueError as e:raise HTTPException(422,str(e))
    user=User(email=email,password_hash=pwh,cuisine='Indian')
    db.add(user);db.commit();seed_user_plan(db,user)
    token,csrf=create_session(db,user)
    response.set_cookie('gd_session',token,httponly=True,secure=secure_cookie(),samesite='lax',max_age=7*86400,path='/')
    return {'user':user_public(user),'csrf':csrf,'message':'Private account created; change the setup token or remove it from environment after onboarding.'}

@app.post('/api/auth/login')
def login(payload:LoginIn,request:Request,response:Response,db:Session=Depends(session_scope)):
    email=payload.email.strip().lower()
    # Restrict repeated failures per account without storing plaintext addresses in attempts.
    attempt_key=digest(email)
    cutoff=(datetime.now(timezone.utc)-timedelta(minutes=15)).isoformat()
    failures=db.query(LoginAttempt).filter(LoginAttempt.login_key==attempt_key,LoginAttempt.attempted_at>=cutoff).count()
    if failures>=8:raise HTTPException(429,'Too many attempts. Try again later.')
    user=db.query(User).filter_by(email=email).first()
    if not user or not verify_password(payload.password,user.password_hash):
        db.add(LoginAttempt(login_key=attempt_key,attempted_at=datetime.now(timezone.utc).isoformat()))
        db.commit()
        raise HTTPException(401,'Incorrect email or password')
    db.query(LoginAttempt).filter_by(login_key=attempt_key).delete()
    token,csrf=create_session(db,user)
    response.set_cookie('gd_session',token,httponly=True,secure=secure_cookie(),samesite='lax',max_age=7*86400,path='/')
    return {'user':user_public(user),'csrf':csrf}

@app.post('/api/auth/signup')
def signup(payload:LoginIn,request:Request,response:Response,db:Session=Depends(session_scope)):
    if os.getenv('ALLOW_SIGNUP','false').lower()!='true':raise HTTPException(403,'New account creation disabled')
    email=payload.email.strip().lower()
    if not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+',email):raise HTTPException(422,'Invalid email')
    if db.query(User).filter_by(email=email).first():raise HTTPException(409,'This email is already registered')
    try:pwh=make_password_hash(payload.password)
    except ValueError as e:raise HTTPException(422,str(e))
    user=User(email=email,password_hash=pwh);db.add(user);db.commit()
    token,csrf=create_session(db,user)
    response.set_cookie('gd_session',token,httponly=True,secure=secure_cookie(),samesite='lax',max_age=7*86400,path='/')
    return {'user':user_public(user),'csrf':csrf}

@app.post('/api/auth/logout')
def logout(request:Request,response:Response,context=Depends(mutation)):
    db,user,sess=context
    db.delete(sess);db.commit();response.delete_cookie('gd_session',path='/')
    return {'ok':True}

@app.post('/api/auth/change-password')
def change_password(data:PasswordIn,context=Depends(mutation)):
    db,user,_=context
    if not verify_password(data.current_password,user.password_hash):raise HTTPException(403,'Current password is incorrect')
    try:user.password_hash=make_password_hash(data.new_password)
    except ValueError as e:raise HTTPException(422,str(e))
    db.query(AuthSession).filter_by(user_id=user.id).delete()
    db.commit()
    return {'ok':True,'message':'Password changed. Please sign in again.'}

@app.get('/api/auth/csrf')
def current_csrf(context=Depends(auth)):
    db,user,sess=context
    # CSRF token is not reversible from its hash. Issue a fresh token on page reload.
    token=secrets.token_urlsafe(32)
    sess.csrf_token_hash=digest(token)
    db.commit()
    return {'csrf':token}

@app.get('/api/me')
def me(context=Depends(auth)):
    db,user,sess=context
    return {'user':user_public(user),'services':{'email_configured':email_ready(),'push_configured':webpush_ready(),'ai_configured':bool(os.getenv('OPENAI_API_KEY'))},'push_subscription_count':db.query(PushSubscription).filter_by(user_id=user.id).count()}

@app.get('/api/dashboard')
def dashboard(context=Depends(auth)):
    db,user,_=context
    tasks=db.query(MonitoringTask).filter_by(user_id=user.id).order_by(MonitoringTask.day,MonitoringTask.occasion).all()
    readings=db.query(GlucoseReading).filter_by(user_id=user.id).order_by(GlucoseReading.measured_at.desc()).all()
    meds=db.query(MedicationDose).filter_by(user_id=user.id).order_by(MedicationDose.day).all()
    summary=compute_summary(readings,tasks)
    last=db.query(AgentRun).filter_by(user_id=user.id).order_by(AgentRun.id.desc()).first()
    return {'profile':user_public(user),'tasks':[{'id':t.id,'day':t.day,'occasion':t.occasion,'source':t.source,'reminder_utc':t.reminder_utc,'complete':any(r.task_id==t.id for r in readings)} for t in tasks],'readings':[{'id':r.id,'value_mmol':r.value_mmol,'measured_at':r.measured_at,'occasion':r.occasion,'task_id':r.task_id,'note':r.note} for r in readings],'medications':[{'id':m.id,'day':m.day,'medication_name':m.medication_name,'units':m.units,'strength_iu':m.strength_iu,'status':m.status,'reminder_utc':m.reminder_utc} for m in meds],'summary':summary,'last_agent_run':{'id':last.id,'status':last.status,'started_at':last.started_at} if last else None}

@app.post('/api/plan/load-example')
def load_example(context=Depends(mutation)):
    db,user,_=context
    seed_user_plan(db,user)
    return {'ok':True,'message':'Fictional 5–18 Oct schedule and four sample supplement dates were loaded. Confirm times before activating any external reminders.'}

@app.post('/api/readings')
def save_reading(payload:ReadIn,context=Depends(mutation)):
    db,user,_=context
    try:value=validate_reading(payload.value,payload.unit,payload.occasion)
    except ValueError as e:raise HTTPException(422,str(e))
    try:
        dt=datetime.fromisoformat(payload.measured_at.replace('Z','+00:00'))
        if dt.tzinfo is None:raise ValueError('Timezone offset required')
        day=dt.astimezone(ZoneInfo(user.timezone)).date().isoformat()
        if dt>datetime.now(timezone.utc)+timedelta(minutes=10):raise ValueError('Cannot record a future measurement')
    except Exception as e:raise HTTPException(422,'Invalid timestamp: '+str(e))
    note=payload.note.strip()
    if len(note)>500:raise HTTPException(422,'Note is too long')
    existing=db.query(GlucoseReading).filter_by(user_id=user.id,measured_at=dt.isoformat(),occasion=payload.occasion).first()
    if existing:raise HTTPException(409,'This measurement timestamp and occasion already exist')
    match=db.query(MonitoringTask).filter_by(user_id=user.id,day=day,occasion=payload.occasion).first()
    if match and db.query(GlucoseReading.id).filter_by(user_id=user.id,task_id=match.id).first():match=None
    r=GlucoseReading(user_id=user.id,task_id=match.id if match else None,value_mmol=value,measured_at=dt.isoformat(),occasion=payload.occasion,source='manual',note=note)
    db.add(r);db.commit();return {'id':r.id,'value_mmol':value,'linked_to_scheduled_task':bool(match)}

@app.delete('/api/readings/{rid}')
def delete_reading(rid:int,context=Depends(mutation)):
    db,user,_=context
    row=db.query(GlucoseReading).filter_by(id=rid,user_id=user.id).first()
    if not row:raise HTTPException(404,'Reading not found')
    db.delete(row);db.commit();return {'ok':True}

@app.get('/api/readings.csv')
def export_csv(context=Depends(auth)):
    db,user,_=context
    readings=db.query(GlucoseReading).filter_by(user_id=user.id).order_by(GlucoseReading.measured_at).all()
    return Response(reading_csv(readings),media_type='text/csv',headers={'Content-Disposition':'attachment; filename=glucodiary_readings.csv','Cache-Control':'no-store'})

@app.get('/api/reports/clinician.csv')
def clinician_report(context=Depends(auth)):
    db,user,_=context
    readings=db.query(GlucoseReading).filter_by(user_id=user.id).order_by(GlucoseReading.measured_at).all()
    tasks=db.query(MonitoringTask).filter_by(user_id=user.id).order_by(MonitoringTask.day,MonitoringTask.occasion).all()
    meds=db.query(MedicationDose).filter_by(user_id=user.id).order_by(MedicationDose.day).all()
    summary=compute_summary(readings,tasks)
    output=io.StringIO();w=csv.writer(output)
    w.writerow(['GlucoDiary AI — patient-reviewed factual record (NOT a clinical diagnosis)'])
    w.writerow(['Account email',user.email]);w.writerow(['Generated UTC',datetime.now(timezone.utc).isoformat()]);w.writerow([])
    w.writerow(['SUMMARY','Value'])
    for k in ['total_readings','scheduled','due','completed_due','missing_due']:w.writerow([k,summary[k]])
    w.writerow([]);w.writerow(['READINGS — time (ISO)','Occasion','mmol/L','Source'])
    for r in readings:w.writerow([r.measured_at,r.occasion,r.value_mmol,r.source])
    w.writerow([]);w.writerow(['SCHEDULE','Occasion','Status'])
    completed={r.task_id for r in readings}
    for t in tasks:w.writerow([t.day,t.occasion,'recorded' if t.id in completed else 'no reading'])
    w.writerow([]);w.writerow(['VITAMIN D — date','Product','Units','Strength IU each','Status'])
    for d in meds:w.writerow([d.day,d.medication_name,d.units,d.strength_iu,d.status])
    return Response(output.getvalue(),media_type='text/csv',headers={'Content-Disposition':'attachment; filename=glucodiary_clinician_report.csv','Cache-Control':'no-store'})

@app.put('/api/reminder-settings')
def reminder_settings(payload:SettingsIn,context=Depends(mutation)):
    db,user,_=context
    try: times=[validate_clock(x) for x in [payload.breakfast_time,payload.lunch_time,payload.dinner_time,payload.sleep_time]]
    except ValueError as e:raise HTTPException(422,str(e))
    if payload.alerts_confirmed and payload.email_enabled and not email_ready():raise HTTPException(409,'Email provider not configured on server')
    if payload.alerts_confirmed and payload.push_enabled and not webpush_ready():raise HTTPException(409,'Web Push VAPID keys not configured')
    if payload.alerts_confirmed and payload.push_enabled and not db.query(PushSubscription.id).filter_by(user_id=user.id).first():raise HTTPException(409,'Subscribe your iPhone/browser to notifications first')
    user.breakfast_time,user.lunch_time,user.dinner_time,user.sleep_time=times
    user.alerts_confirmed=payload.alerts_confirmed;user.email_enabled=payload.email_enabled;user.push_enabled=payload.push_enabled
    try:update_reminder_times(db,user)
    except ValueError as e:db.rollback();raise HTTPException(422,str(e))
    db.commit()
    return {'ok':True,'active':user.alerts_confirmed,'note':'Scheduled reminders require the configured runner to invoke /internal/dispatch regularly.'}

@app.put('/api/medications/{medid}')
def med_status(medid:int,data:DoseIn,context=Depends(mutation)):
    db,user,_=context
    if data.status not in ('scheduled','taken','skipped'):raise HTTPException(422,'Invalid status')
    med=db.query(MedicationDose).filter_by(id=medid,user_id=user.id).first()
    if not med:raise HTTPException(404,'Medication entry not found')
    med.status=data.status
    med.confirmed_at=datetime.now(timezone.utc).isoformat() if data.status=='taken' else None
    db.commit();return {'ok':True,'status':med.status}

@app.put('/api/food')
def food_settings(payload:FoodIn,context=Depends(mutation)):
    db,user,_=context
    allowed={'Indian','Mediterranean','East Asian','Any'}
    if payload.enabled and not payload.allergies_confirmed:raise HTTPException(422,'Please review your allergies and exclusions before enabling meal ideas')
    if payload.cuisine not in allowed:raise HTTPException(422,'Unsupported cuisine')
    if any(len(s)>80 for s in payload.allergens+payload.avoid) or len(payload.allergens)>30 or len(payload.avoid)>40:raise HTTPException(422,'Too many entries')
    user.food_enabled=payload.enabled;user.cuisine=payload.cuisine
    user.allergens=json.dumps(payload.allergens);user.avoid_ingredients=json.dumps(payload.avoid)
    db.commit();return {'ok':True}

@app.get('/api/food')
def food_recommendations(context=Depends(auth)):
    db,user,_=context
    if not user.food_enabled:return {'enabled':False,'recipes':[],'notice':'Optional feature is off.'}
    allergies=json.loads(user.allergens or '[]');avoid=json.loads(user.avoid_ingredients or '[]')
    return {'enabled':True,'recipes':eligible_recipes(user.cuisine,allergies,avoid),'notice':'Illustrative recipes only. Not clinically approved; confirm ingredients, packaged-food labels and allergen cross-contact independently.'}

@app.put('/api/consent/ai')
def ai_consent(data:ConsentIn,context=Depends(mutation)):
    db,user,_=context;user.ai_consent=data.enabled;db.commit();return {'ok':True,'enabled':user.ai_consent}

@app.post('/api/agents/run')
def agents_run(context=Depends(mutation)):
    db,user,_=context
    if not user.ai_consent:raise HTTPException(403,'Enable AI processing consent first')
    if not os.getenv('OPENAI_API_KEY'):raise HTTPException(503,'AI provider key not configured')
    readings=db.query(GlucoseReading).filter_by(user_id=user.id).all()
    if len(readings)<2:raise HTTPException(422,'Record at least two glucose measurements first')
    tasks=db.query(MonitoringTask).filter_by(user_id=user.id).all()
    try:return run_insight_agents(db,user,readings,tasks)
    except RuntimeError as e:raise HTTPException(502,str(e))

@app.get('/api/agents/runs/{run_id}')
def agent_trace(run_id:int,context=Depends(auth)):
    db,user,_=context
    run=db.query(AgentRun).filter_by(id=run_id,user_id=user.id).first()
    if not run:raise HTTPException(404,'Run not found')
    steps=db.query(AgentStep).filter_by(run_id=run.id).order_by(AgentStep.sequence).all()
    return {'id':run.id,'status':run.status,'model':run.model_name,'result':json.loads(run.result),'steps':[{'agent':s.agent,'status':s.status,'output':json.loads(s.output)} for s in steps]}

@app.get('/api/push/vapid')
def public_vapid(context=Depends(auth)):
    return {'public_key':os.getenv('VAPID_PUBLIC_KEY',''),'configured':webpush_ready()}

@app.post('/api/push/subscribe')
def subscribe_push(data:PushIn,context=Depends(mutation)):
    db,user,_=context
    if not webpush_ready():raise HTTPException(503,'Server push keys not configured')
    if not data.endpoint.startswith('https://') or len(data.endpoint)>2048:raise HTTPException(422,'Invalid push endpoint')
    a=data.keys.get('auth');p=data.keys.get('p256dh')
    if not isinstance(a,str) or not isinstance(p,str) or not a or not p:raise HTTPException(422,'Push keys missing')
    row=db.query(PushSubscription).filter_by(endpoint=data.endpoint).first()
    if row and row.user_id!=user.id:raise HTTPException(409,'Push endpoint belongs to a different account')
    if row:row.auth=a;row.p256dh=p
    else:db.add(PushSubscription(user_id=user.id,endpoint=data.endpoint,p256dh=p,auth=a))
    db.commit();return {'ok':True}

@app.post('/api/reminders/test')
def test_reminder(context=Depends(mutation)):
    db,user,_=context
    result={'email':'not requested','push':'not requested'}
    if user.email_enabled:
        if not email_ready():result['email']='not configured'
        else:
            try:send_email(user.email,'GlucoDiary test notification','Your GlucoDiary email reminder setup is working. No health details are included.');result['email']='sent'
            except Exception as e:result['email']='failed: '+type(e).__name__
    if user.push_enabled:
        subs=db.query(PushSubscription).filter_by(user_id=user.id).all()
        if not subs:result['push']='not subscribed'
        else:
            try:send_push(subs,'GlucoDiary test notification','Your push notification setup is working.');result['push']='sent'
            except Exception as e:result['push']='failed: '+type(e).__name__
    return result

@app.post('/internal/dispatch')
def dispatch(request:Request,db:Session=Depends(session_scope)):
    import hmac
    expected=os.getenv('REMINDER_RUNNER_SECRET','')
    provided=request.headers.get('X-Runner-Token','')
    if not expected or not hmac.compare_digest(provided,expected):raise HTTPException(403,'Unauthorised dispatcher')
    return dispatch_due(db)

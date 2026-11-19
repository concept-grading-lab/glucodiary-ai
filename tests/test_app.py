from datetime import datetime,timedelta,timezone
import json,types
import pytest
from app.services import (schedule_blueprint,vitd_blueprint,validate_reading,update_reminder_times,
    compute_summary,eligible_recipes,utc_reminder)
from app.db import SessionLocal
from app.models import User,MonitoringTask,GlucoseReading,MedicationDose,ReminderDelivery
from app.notifications import dispatch_due
from app.agents import run_insight_agents,unsafe


def test_schedule_length(): assert len(schedule_blueprint())==28
def test_schedule_starts_ends():
    d=schedule_blueprint();assert (d[0]['day'],d[1]['occasion'])==('2026-10-05','before_lunch');assert d[-1]['day']=='2026-10-18'
def test_schedule_every_day_breakfast():assert sum(t['occasion']=='before_breakfast' for t in schedule_blueprint())==14
def test_rotating_lunch():assert sum(t['occasion']=='before_lunch' for t in schedule_blueprint())==5
def test_rotating_dinner():assert sum(t['occasion']=='before_dinner' for t in schedule_blueprint())==5
def test_rotating_bed():assert sum(t['occasion']=='before_sleep' for t in schedule_blueprint())==4
def test_schedule_synthetic_provenance():assert sum(t['source']=='synthetic_demo' for t in schedule_blueprint())==28
def test_schedule_example_total():assert sum(t['source']=='synthetic_demo' for t in schedule_blueprint())==28
def test_medication_four():assert len(vitd_blueprint())==4
def test_medication_tuesdays():assert all(datetime.fromisoformat(m['day']).weekday()==1 for m in vitd_blueprint())
def test_medication_first_taken():assert vitd_blueprint()[0]['status']=='taken'
def test_medication_last():assert vitd_blueprint()[-1]['day']=='2026-10-27'
def test_glucose_accept():assert validate_reading(7.4,'mmol/L','before_lunch')==7.4
@pytest.mark.parametrize('v',[0,-1,70,True])
def test_glucose_bounds(v):
    with pytest.raises(ValueError):validate_reading(v,'mmol/L','before_lunch')
def test_glucose_unit():
    with pytest.raises(ValueError):validate_reading(150,'mg/dL','before_lunch')
def test_glucose_context():
    with pytest.raises(ValueError):validate_reading(7,'mmol/L','floating')
def test_utc_reminder():assert utc_reminder('2026-11-24','12:30','Europe/London').startswith('2026-11-24T12:30:00')
def test_dst_conversion():assert utc_reminder('2026-07-24','12:30','Europe/London').startswith('2026-07-24T11:30:00')
def test_dst_nonexistent_time():
    with pytest.raises(ValueError):utc_reminder('2026-03-29','01:30','Europe/London')
def test_food_opt_in_filters():assert all('milk' not in r['allergens'] for r in eligible_recipes('Indian',['milk'],[]))
def test_food_excluded_ingredient():assert all('onion' not in r['ingredients'] for r in eligible_recipes('Indian',[],['onion']))
def test_login_and_profile(client,account):
    r=client.get('/api/me');assert r.status_code==200;assert r.json()['user']['email']==account['email']
def test_auth_cookie_missing_csrf(client,account):
    r=client.post('/api/plan/load-example');assert r.status_code==403
def test_session_csrf_refresh(client,account):
    r=client.get('/api/auth/csrf');assert r.status_code==200 and len(r.json()['csrf'])>24
    # restore a valid csrf for subsequent tests because sessions share a cookie
    account['csrf']=r.json()['csrf']
def test_scheduling_api(client,account):
    r=client.post('/api/plan/load-example',headers={'X-CSRF-Token':account['csrf']});assert r.status_code==200,r.text
    d=client.get('/api/dashboard').json();assert len(d['tasks'])==28 and len(d['medications'])==4
    assert d['medications'][0]['status']=='taken'
def test_food_default_off(client,account):
    r=client.get('/api/food');assert r.json()['enabled'] is False and r.json()['recipes']==[]
def test_food_enable(client,account):
    r=client.put('/api/food',headers={'X-CSRF-Token':account['csrf']},json={'enabled':True,'allergies_confirmed':True,'cuisine':'Indian','allergens':['milk'],'avoid':[]});assert r.status_code==200
    data=client.get('/api/food').json();assert data['enabled'] and all('milk' not in x['allergens'] for x in data['recipes'])
def test_reading_entry_persistent(client,account):
    p={'value':7.4,'unit':'mmol/L','occasion':'before_lunch','measured_at':'2026-10-05T12:30:00+00:00','note':'synthetic entry'}
    r=client.post('/api/readings',headers={'X-CSRF-Token':account['csrf']},json=p);assert r.status_code==200,r.text
    assert client.get('/api/dashboard').json()['summary']['total_readings']==1
    assert client.post('/api/readings',headers={'X-CSRF-Token':account['csrf']},json=p).status_code==409
    assert 'synthetic entry' in client.get('/api/readings.csv').text

def test_reading_no_future(client,account):
    p={'value':7,'occasion':'before_sleep','measured_at':(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()}
    assert client.post('/api/readings',headers={'X-CSRF-Token':account['csrf']},json=p).status_code==422

def test_medication_status_update(client,account):
    client.post('/api/plan/load-example',headers={'X-CSRF-Token':account['csrf']})
    mid=client.get('/api/dashboard').json()['medications'][1]['id']
    assert client.put('/api/medications/'+str(mid),headers={'X-CSRF-Token':account['csrf']},json={'status':'taken'}).status_code==200
    assert client.get('/api/dashboard').json()['medications'][1]['status']=='taken'

def test_reminder_activate_requires_provider(client,account):
    client.post('/api/plan/load-example',headers={'X-CSRF-Token':account['csrf']})
    v={'breakfast_time':'07:30','lunch_time':'12:30','dinner_time':'18:30','sleep_time':'22:00','email_enabled':True,'push_enabled':False,'alerts_confirmed':True}
    r=client.put('/api/reminder-settings',headers={'X-CSRF-Token':account['csrf']},json=v)
    assert r.status_code==409

def test_reminder_manual_times(client,account):
    client.post('/api/plan/load-example',headers={'X-CSRF-Token':account['csrf']})
    v={'breakfast_time':'07:30','lunch_time':'12:30','dinner_time':'18:30','sleep_time':'22:00','email_enabled':False,'push_enabled':False,'alerts_confirmed':True}
    r=client.put('/api/reminder-settings',headers={'X-CSRF-Token':account['csrf']},json=v)
    assert r.status_code==200,r.text
    d=client.get('/api/dashboard').json();assert all(t['reminder_utc'] for t in d['tasks'])

def test_agent_gate(client,account):
    assert client.post('/api/agents/run',headers={'X-CSRF-Token':account['csrf']}).status_code==403
    assert client.put('/api/consent/ai',headers={'X-CSRF-Token':account['csrf']},json={'enabled':True}).status_code==200
    assert client.post('/api/agents/run',headers={'X-CSRF-Token':account['csrf']}).status_code==503

def test_agent_unsafe_guard():assert unsafe('increase your insulin dose today')
def test_agent_safe_guard():assert not unsafe('Three before-lunch readings were recorded.')

class FakeOpenAI:
    def __init__(self,approved=True,unsafe_text=False):
        self.approved=approved;self.unsafe_text=unsafe_text;self.calls=[]
        self.chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=self.create))
    def create(self,**kwargs):
        self.calls.append(kwargs)
        i=len(self.calls)
        if i==1:obj={'findings':['Two observations are available'],'limitations':['Few readings']}
        elif i==2:obj={'summary':'Increase your insulin dose.' if self.unsafe_text else 'You have two recorded glucose readings.','questions_for_clinician':['Are my monitoring times suitable?']}
        else:obj={'approved':self.approved,'reason':'Safety checked'}
        return types.SimpleNamespace(choices=[types.SimpleNamespace(message=types.SimpleNamespace(content=json.dumps(obj)))])

def test_actual_agent_pipeline_with_mocked_provider(client,account):
    client.post('/api/plan/load-example',headers={'X-CSRF-Token':account['csrf']})
    for date,value in [('2026-10-05T07:30:00+00:00',9.0),('2026-10-06T07:30:00+00:00',8.4)]:
        client.post('/api/readings',headers={'X-CSRF-Token':account['csrf']},json={'value':value,'occasion':'before_breakfast','measured_at':date})
    with SessionLocal() as db:
        user=db.query(User).filter_by(email=account['email']).one();user.ai_consent=True;db.commit()
        r=db.query(GlucoseReading).filter_by(user_id=user.id).all();t=db.query(MonitoringTask).filter_by(user_id=user.id).all()
        fake=FakeOpenAI();out=run_insight_agents(db,user,r,t,client=fake)
        assert out['approved'] and len(fake.calls)==3
        assert out['run_id'] and out['status']=='completed'

def test_agent_pipeline_safety_hold(client,account):
    with SessionLocal() as db:
        user=db.query(User).filter_by(email=account['email']).one();user.ai_consent=True;db.commit()
        t=db.query(MonitoringTask).filter_by(user_id=user.id).all()
        r=[GlucoseReading(user_id=user.id,value_mmol=6,measured_at='2026-10-05T07:30:00+00:00',occasion='before_breakfast'),GlucoseReading(user_id=user.id,value_mmol=8,measured_at='2026-10-06T07:30:00+00:00',occasion='before_breakfast')]
        out=run_insight_agents(db,user,r,t,client=FakeOpenAI(unsafe_text=True))
        assert out['approved'] is False and out['status']=='held'

def test_internal_endpoint_requires_secret(client):
    assert client.post('/internal/dispatch').status_code==403

def test_dispatch_mocks_delivery(client,account):
    from app.notifications import dispatch_due
    with SessionLocal() as db:
        user=db.query(User).filter_by(email=account['email']).one()
        user.alerts_confirmed=True;user.email_enabled=True;user.push_enabled=False
        now=datetime.now(timezone.utc)
        task=MonitoringTask(user_id=user.id,day=now.date().isoformat(),occasion='other',source='user',reminder_utc=(now-timedelta(minutes=1)).isoformat())
        db.add(task);db.commit()
        calls=[]
        def fake_email(to,sub,body):calls.append((to,sub))
        a=dispatch_due(db,now=now,send_email_fn=fake_email)
        b=dispatch_due(db,now=now,send_email_fn=fake_email)
        assert a['sent']==1 and b['sent']==0 and len(calls)==1

def test_auth_isolation(client,account):
    first=client.get('/api/dashboard').json()['readings']
    another=client.post('/api/auth/signup',json={'email':'separate-'+account['email'],'password':'LongEnoughPassphrase123!'}).json()
    assert client.get('/api/dashboard').json()['readings']==[]
    if first:
        x=client.delete('/api/readings/'+str(first[0]['id']),headers={'X-CSRF-Token':another['csrf']})
        assert x.status_code==404

def test_password_not_stored_plaintext(client,account):
    with SessionLocal() as db:
        user=db.query(User).filter_by(email=account['email']).one()
        assert account['password'] not in user.password_hash
        assert user.password_hash.startswith('$argon2id$')


def test_food_requires_allergy_review(client,account):
    p={'enabled':True,'cuisine':'Indian','allergens':[],'avoid':[]}
    r=client.put('/api/food',headers={'X-CSRF-Token':account['csrf']},json=p)
    assert r.status_code==422

def test_clinician_report_access(client,account):
    r=client.get('/api/reports/clinician.csv')
    assert r.status_code==200 and 'GlucoDiary' in r.text and 'VITAMIN D' in r.text

def test_bootstrap_rejects_without_token(client):
    r=client.post('/api/setup',json={'setup_token':'unconfigured','email':'user@example.test','password':'SomeLongPassword_2026'})
    assert r.status_code==403

def test_login_rate_limit(client,account):
    for _ in range(8):
        assert client.post('/api/auth/login',json={'email':account['email'],'password':'incorrect-password'}).status_code==401
    assert client.post('/api/auth/login',json={'email':account['email'],'password':'incorrect-password'}).status_code==429

def test_push_subscription_requires_provider(client,account):
    p={'endpoint':'https://push.example.invalid/test','keys':{'auth':'key','p256dh':'key'}}
    assert client.post('/api/push/subscribe',headers={'X-CSRF-Token':account['csrf']},json=p).status_code==503

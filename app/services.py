import json,re,csv,io
from datetime import datetime,date,timedelta,timezone
from zoneinfo import ZoneInfo
from sqlalchemy import func
from fastapi import HTTPException
from .models import MonitoringTask,GlucoseReading,MedicationDose
OCCASIONS=('before_breakfast','before_lunch','before_dinner','before_sleep','other')
LABELS={'before_breakfast':'Before breakfast','before_lunch':'Before lunch','before_dinner':'Before dinner','before_sleep':'Before sleep','other':'Other'}
ROTATING=('before_lunch','before_dinner','before_sleep')
DAYS=(date(2026,10,5),date(2026,10,18))

# Public-source backend seed: fictional, not based on a real patient or universal care plan.
def dates_between(a,b):
    while a<=b:
        yield a
        a+=timedelta(days=1)

def schedule_blueprint():
    out=[]
    for offset,day in enumerate(dates_between(*DAYS)):
        for occ in ('before_breakfast',ROTATING[offset%3]):
            out.append(dict(day=day.isoformat(),occasion=occ,source='synthetic_demo'))
    return out

def vitd_blueprint():
    start=date(2026,10,6)
    return [dict(day=(start+timedelta(days=7*i)).isoformat(),medication_name='Synthetic supplement A',strength_iu=1000,units=1,status='taken' if i==0 else 'scheduled') for i in range(4)]

def seed_user_plan(db,user):
    have=db.query(MonitoringTask.id).filter_by(user_id=user.id).first()
    if not have:
        for row in schedule_blueprint(): db.add(MonitoringTask(user_id=user.id,**row))
    have_med=db.query(MedicationDose.id).filter_by(user_id=user.id).first()
    if not have_med:
        for row in vitd_blueprint():db.add(MedicationDose(user_id=user.id,**row))
    db.commit()

def validate_clock(v):
    if not isinstance(v,str) or re.fullmatch(r'([01]\d|2[0-3]):[0-5]\d',v) is None:
        raise ValueError('Time must be HH:MM (24-hour format)')
    return v

def utc_reminder(day, time_local, tz):
    validate_clock(time_local)
    local=datetime.fromisoformat(day+'T'+time_local).replace(tzinfo=ZoneInfo(tz))
    # Roundtrip guard for non-existing wall times (DST changes)
    utc=local.astimezone(timezone.utc)
    if utc.astimezone(ZoneInfo(tz)).replace(tzinfo=None)!=local.replace(tzinfo=None):
        raise ValueError('Time does not exist in this timezone on this date')
    return utc.isoformat(timespec='seconds')

def update_reminder_times(db,user):
    mapping={'before_breakfast':user.breakfast_time,'before_lunch':user.lunch_time,'before_dinner':user.dinner_time,'before_sleep':user.sleep_time}
    for task in db.query(MonitoringTask).filter_by(user_id=user.id):
        task.reminder_utc=utc_reminder(task.day,mapping[task.occasion],user.timezone)
    for dose in db.query(MedicationDose).filter_by(user_id=user.id):
        dose.reminder_utc=utc_reminder(dose.day,user.lunch_time,user.timezone)
    db.commit()

def validate_reading(value,unit,occasion):
    if not isinstance(value,(int,float)) or isinstance(value,bool):raise ValueError('Reading must be a number')
    if not (0.1 <= float(value) <= 60):raise ValueError('Reading outside supported input range; recheck units and meter')
    if unit!='mmol/L':raise ValueError('Only mmol/L is supported in this version; convert explicitly before entry')
    if occasion not in OCCASIONS:raise ValueError('Invalid occasion')
    return round(float(value),2)

def compute_summary(readings,tasks,now=None):
    now=now or datetime.now(timezone.utc)
    per={}
    for r in readings:
        if r.occasion not in per:per[r.occasion]=[]
        per[r.occasion].append(float(r.value_mmol))
    grouped={occ:{'count':len(vals),'average':round(sum(vals)/len(vals),2),'minimum':min(vals),'maximum':max(vals)} for occ,vals in per.items()}
    recorded={r.task_id for r in readings if r.task_id is not None}
    due=[t for t in tasks if t.reminder_utc and datetime.fromisoformat(t.reminder_utc)<=now]
    # when no reminder schedule confirmed, due assessment based only on day, not hour
    if not due and all(not t.reminder_utc for t in tasks):
        due=[t for t in tasks if t.day < now.date().isoformat()]
    return {'total_readings':len(readings),'summary_by_occasion':grouped,'scheduled':len(tasks),'due':len(due),'completed_due':sum(t.id in recorded for t in due),'missing_due':sum(t.id not in recorded for t in due), 'data_quality_note':'These are descriptive measurements, not a diagnosis or treatment recommendation.'}

def reading_csv(readings):
    out=io.StringIO();w=csv.writer(out);w.writerow(['Date/time (ISO 8601)','Occasion','Blood glucose (mmol/L)','Source','Note'])
    for r in readings:w.writerow([r.measured_at,LABELS.get(r.occasion,r.occasion),r.value_mmol,r.source,r.note])
    return out.getvalue()

RECIPES=[
 {'name':'Moong dal chilla with vegetables','cuisine':'Indian','allergens':[],'ingredients':['moong dal','onion','spinach','spices'],'diet':'vegan'},
 {'name':'Paneer bhurji with vegetables','cuisine':'Indian','allergens':['milk'],'ingredients':['paneer','tomato','capsicum'],'diet':'vegetarian'},
 {'name':'Chana and cucumber salad','cuisine':'Indian','allergens':[],'ingredients':['chickpeas','cucumber','tomato','lemon'],'diet':'vegan'},
 {'name':'Masoor dal and sautéed vegetables','cuisine':'Indian','allergens':[],'ingredients':['red lentils','cauliflower','spices'],'diet':'vegan'},
 {'name':'Vegetable stir-fry with tofu','cuisine':'East Asian','allergens':['soya'],'ingredients':['tofu','broccoli','soya'],'diet':'vegan'},
 {'name':'Roasted vegetable quinoa bowl','cuisine':'Mediterranean','allergens':[],'ingredients':['quinoa','courgette','pepper'],'diet':'vegan'}]

def eligible_recipes(cuisine,allergens,avoid):
    banned={a.lower().strip() for a in allergens+avoid if a.strip()}
    return [r for r in RECIPES if (cuisine=='Any' or r['cuisine']==cuisine) and not (set(map(str.lower,r['allergens']))&banned) and not (set(map(str.lower,r['ingredients']))&banned)]

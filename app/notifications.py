"""Actual email and Web Push dispatch. Sending requires credentials and explicit patient opt-in."""
import os,json,smtplib,ssl
from email.message import EmailMessage
from datetime import datetime,timedelta,timezone
import httpx
from .models import MonitoringTask,MedicationDose,GlucoseReading,PushSubscription,ReminderDelivery,User
from .services import LABELS

def email_ready():
    return bool(os.getenv('RESEND_API_KEY') or (os.getenv('SMTP_USERNAME') and os.getenv('SMTP_PASSWORD') and os.getenv('SMTP_FROM')))

def webpush_ready():
    return bool(os.getenv('VAPID_PRIVATE_KEY') and os.getenv('VAPID_PUBLIC_KEY') and os.getenv('VAPID_SUBJECT'))

def send_email(to,subject,body):
    if os.getenv('RESEND_API_KEY'):
        with httpx.Client(timeout=15) as client:
            resp=client.post('https://api.resend.com/emails',headers={'Authorization':'Bearer '+os.environ['RESEND_API_KEY'],'Content-Type':'application/json'},json={'from':os.getenv('RESEND_FROM','GlucoDiary <onboarding@resend.dev>'),'to':[to],'subject':subject,'text':body})
            resp.raise_for_status()
        return 'resend'
    if not email_ready():raise RuntimeError('Email SMTP credentials are not configured')
    message=EmailMessage();message['From']=os.environ['SMTP_FROM'];message['To']=to;message['Subject']=subject;message.set_content(body)
    with smtplib.SMTP(os.getenv('SMTP_HOST','smtp.gmail.com'),int(os.getenv('SMTP_PORT','587')),timeout=15) as smtp:
        smtp.starttls(context=ssl.create_default_context())
        smtp.login(os.environ['SMTP_USERNAME'],os.environ['SMTP_PASSWORD']);smtp.send_message(message)
    return 'smtp'

def send_push(subscriptions,title,body):
    if not webpush_ready():raise RuntimeError('VAPID credentials are not configured')
    from pywebpush import webpush
    for sub in subscriptions:
        webpush(subscription_info={'endpoint':sub.endpoint,'keys':{'p256dh':sub.p256dh,'auth':sub.auth}},data=json.dumps({'title':title,'body':body,'url':'/'}),vapid_private_key=os.environ['VAPID_PRIVATE_KEY'].replace('\\n','\n'),vapid_claims={'sub':os.environ['VAPID_SUBJECT']})
    return len(subscriptions)

def dispatch_due(db, now=None, send_email_fn=send_email, send_push_fn=send_push):
    """Idempotent-ish dispatch protected by a DB unique constraint, single scheduler invocation.
    Multiple simultaneous runners may race: a production queue/claim-lock is required for strict exactly-once.
    The system intentionally avoids late (>90 min) reminders.
    """
    now=now or datetime.now(timezone.utc)
    now_iso=now.isoformat()
    start=(now-timedelta(minutes=90)).isoformat()
    results={'eligible':0,'sent':0,'failed':0,'skipped':0,'errors':[]}
    users=db.query(User).filter(User.alerts_confirmed.is_(True)).all()
    for user in users:
        tasks=db.query(MonitoringTask).filter(MonitoringTask.user_id==user.id, MonitoringTask.reminder_utc<=now_iso,MonitoringTask.reminder_utc>=start).all()
        doses=db.query(MedicationDose).filter(MedicationDose.user_id==user.id,MedicationDose.reminder_utc<=now_iso,MedicationDose.reminder_utc>=start,MedicationDose.status=='scheduled').all()
        candidates=[('glucose',t,t.occasion) for t in tasks]+[('vitamin_d',d,'with lunch') for d in doses]
        for kind,source,occasion in candidates:
            if kind=='glucose' and db.query(GlucoseReading.id).filter_by(user_id=user.id,task_id=source.id).first():
                results['skipped']+=1;continue
            title='GlucoDiary reminder'
            body=('Scheduled glucose check: '+LABELS[occasion] if kind=='glucose' else 'Scheduled supplement reminder with lunch. Follow clinician instructions.')
            channels=[]
            if user.email_enabled: channels.append('email')
            subs=db.query(PushSubscription).filter_by(user_id=user.id).all()
            if user.push_enabled and subs:channels.append('push')
            for channel in channels:
                if db.query(ReminderDelivery.id).filter_by(user_id=user.id,kind=kind,source_id=source.id,channel=channel,status='sent').first():
                    results['skipped']+=1;continue
                results['eligible']+=1
                prev=db.query(ReminderDelivery).filter_by(user_id=user.id,kind=kind,source_id=source.id,channel=channel).first()
                if not prev:
                    prev=ReminderDelivery(user_id=user.id,kind=kind,source_id=source.id,channel=channel, status='pending',attempted_at=now_iso)
                    db.add(prev);db.flush()
                try:
                    if channel=='email':send_email_fn(user.email,title,body)
                    else:send_push_fn(subs,title,body)
                    prev.status='sent';prev.attempted_at=now_iso;prev.detail='';results['sent']+=1
                except Exception as e:
                    prev.status='failed';prev.attempted_at=now_iso;prev.detail=type(e).__name__+': '+str(e)[:90]
                    results['failed']+=1;results['errors'].append({'kind':kind,'channel':channel,'error':type(e).__name__})
                db.commit()
    return results

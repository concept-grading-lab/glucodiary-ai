from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, UniqueConstraint, Float
from sqlalchemy.orm import relationship
from .db import Base

def utcnow(): return datetime.now(timezone.utc)

class User(Base):
    __tablename__='users'
    id=Column(Integer,primary_key=True)
    email=Column(String(255),unique=True,nullable=False,index=True)
    password_hash=Column(String(255),nullable=False)
    timezone=Column(String(60),default='Europe/London',nullable=False)
    created_at=Column(DateTime(timezone=True),default=utcnow)
    alerts_confirmed=Column(Boolean,default=False,nullable=False)
    email_enabled=Column(Boolean,default=False,nullable=False)
    push_enabled=Column(Boolean,default=False,nullable=False)
    ai_consent=Column(Boolean,default=False,nullable=False)
    food_enabled=Column(Boolean,default=False,nullable=False)
    cuisine=Column(String(80),default='Indian')
    allergens=Column(Text,default='[]')
    avoid_ingredients=Column(Text,default='[]')
    breakfast_time=Column(String(5),default='07:30')
    lunch_time=Column(String(5),default='12:30')
    dinner_time=Column(String(5),default='18:30')
    sleep_time=Column(String(5),default='22:00')

class AuthSession(Base):
    __tablename__='auth_sessions'
    id=Column(Integer,primary_key=True)
    user_id=Column(Integer,ForeignKey('users.id'),nullable=False,index=True)
    token_hash=Column(String(64),unique=True,nullable=False)
    csrf_token_hash=Column(String(64),nullable=False)
    expires_at=Column(DateTime(timezone=True),nullable=False)
    created_at=Column(DateTime(timezone=True),default=utcnow)

class MonitoringTask(Base):
    __tablename__='monitoring_tasks'
    __table_args__=(UniqueConstraint('user_id','day','occasion',name='uniq_monitoring_task'),)
    id=Column(Integer,primary_key=True)
    user_id=Column(Integer,ForeignKey('users.id'),nullable=False,index=True)
    day=Column(String(10),nullable=False,index=True)
    occasion=Column(String(30),nullable=False)
    source=Column(String(30),nullable=False,default='clinician_confirmed')
    # Timestamps are revised when reminder times are confirmed.
    reminder_utc=Column(String(40),nullable=True)
    created_at=Column(DateTime(timezone=True),default=utcnow)

class GlucoseReading(Base):
    __tablename__='glucose_readings'
    id=Column(Integer,primary_key=True)
    user_id=Column(Integer,ForeignKey('users.id'),nullable=False,index=True)
    task_id=Column(Integer,ForeignKey('monitoring_tasks.id'),nullable=True)
    value_mmol=Column(Float,nullable=False)
    measured_at=Column(String(40),nullable=False)
    occasion=Column(String(30),nullable=False)
    source=Column(String(30),nullable=False,default='manual')
    note=Column(String(500),default='')
    created_at=Column(DateTime(timezone=True),default=utcnow)

class MedicationDose(Base):
    __tablename__='medication_doses'
    __table_args__=(UniqueConstraint('user_id','day','medication_name',name='uniq_med_date'),)
    id=Column(Integer,primary_key=True)
    user_id=Column(Integer,ForeignKey('users.id'),nullable=False,index=True)
    day=Column(String(10),nullable=False)
    medication_name=Column(String(120),nullable=False)
    units=Column(Integer,nullable=False)
    strength_iu=Column(Integer,nullable=False)
    status=Column(String(20),nullable=False,default='scheduled')
    reminder_utc=Column(String(40),nullable=True)
    confirmed_at=Column(String(40),nullable=True)

class PushSubscription(Base):
    __tablename__='push_subscriptions'
    id=Column(Integer,primary_key=True)
    user_id=Column(Integer,ForeignKey('users.id'),nullable=False,index=True)
    endpoint=Column(Text,nullable=False,unique=True)
    p256dh=Column(Text,nullable=False)
    auth=Column(Text,nullable=False)
    created_at=Column(DateTime(timezone=True),default=utcnow)

class ReminderDelivery(Base):
    __tablename__='reminder_deliveries'
    __table_args__=(UniqueConstraint('user_id','kind','source_id','channel',name='uniq_delivery'),)
    id=Column(Integer,primary_key=True)
    user_id=Column(Integer,ForeignKey('users.id'),nullable=False,index=True)
    kind=Column(String(20),nullable=False)
    source_id=Column(Integer,nullable=False)
    channel=Column(String(20),nullable=False)
    status=Column(String(20),nullable=False)
    attempted_at=Column(String(40),nullable=False)
    detail=Column(String(160),nullable=False,default='')

class AgentRun(Base):
    __tablename__='agent_runs'
    id=Column(Integer,primary_key=True)
    user_id=Column(Integer,ForeignKey('users.id'),nullable=False,index=True)
    started_at=Column(String(40),nullable=False)
    model_name=Column(String(80),nullable=False)
    result=Column(Text,nullable=False)
    status=Column(String(20),nullable=False)

class AgentStep(Base):
    __tablename__='agent_steps'
    id=Column(Integer,primary_key=True)
    run_id=Column(Integer,ForeignKey('agent_runs.id'),nullable=False,index=True)
    sequence=Column(Integer,nullable=False)
    agent=Column(String(50),nullable=False)
    status=Column(String(20),nullable=False)
    output=Column(Text,nullable=False)

class LoginAttempt(Base):
    __tablename__='login_attempts'
    id=Column(Integer,primary_key=True)
    login_key=Column(String(64),nullable=False,index=True)
    attempted_at=Column(String(40),nullable=False)

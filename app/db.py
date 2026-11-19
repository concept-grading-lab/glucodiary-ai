import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

def normalize_url(url):
    if url.startswith('postgres://'):
        return 'postgresql+psycopg://' + url[len('postgres://'):]
    if url.startswith('postgresql://') and '+psycopg' not in url:
        return 'postgresql+psycopg://' + url[len('postgresql://'):]
    return url

def get_engine():
    url = normalize_url(os.getenv('DATABASE_URL', 'sqlite:///./data/glucodiary.db'))
    if url.startswith('sqlite:///') and ':memory:' not in url:
        Path(url[len('sqlite:///'):]).parent.mkdir(parents=True, exist_ok=True)
    return create_engine(url, pool_pre_ping=True, connect_args={'check_same_thread':False} if url.startswith('sqlite:') else {})

engine = get_engine()
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)

def init_db():
    from . import models  # noqa: F401
    Base.metadata.create_all(bind=engine)

def session_scope():
    db=SessionLocal()
    try:
        yield db
    finally:
        db.close()

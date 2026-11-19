import os,tempfile,pytest
from pathlib import Path
# Make all automated tests use a disposable private database, never a patient's DB.
_testdir=tempfile.TemporaryDirectory()
os.environ['DATABASE_URL']='sqlite:///'+str(Path(_testdir.name)/'test.sqlite')
os.environ['ALLOW_SIGNUP']='true'
os.environ['COOKIE_SECURE']='false'
os.environ.pop('OPENAI_API_KEY',None)
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture(scope='session')
def client():
    with TestClient(app) as c:yield c

@pytest.fixture
def account(client):
    import uuid
    email=f'test-{uuid.uuid4().hex[:12]}@example.invalid'
    p='TestOnly_Passphrase_2026!'
    r=client.post('/api/auth/signup',json={'email':email,'password':p})
    assert r.status_code==200, r.text
    return {'email':email,'password':p,'csrf':r.json()['csrf']}

@pytest.fixture
def auth_headers(account):
    return {'X-CSRF-Token':account['csrf']}

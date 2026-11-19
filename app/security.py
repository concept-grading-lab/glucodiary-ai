import hashlib, hmac, secrets, os
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, Request
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError
from .models import AuthSession, User

password_hasher=PasswordHasher(time_cost=2,memory_cost=19456,parallelism=1)
SESSION_DAYS=7

def make_password_hash(p):
    if len(p)<12: raise ValueError('Password must have at least 12 characters')
    return password_hasher.hash(p)

def verify_password(p,h):
    try: return password_hasher.verify(h,p)
    except (VerifyMismatchError,VerificationError): return False

def digest(text): return hashlib.sha256(text.encode()).hexdigest()

def create_session(db,user):
    token=secrets.token_urlsafe(40)
    csrf=secrets.token_urlsafe(32)
    db.add(AuthSession(user_id=user.id, token_hash=digest(token),csrf_token_hash=digest(csrf),expires_at=datetime.now(timezone.utc)+timedelta(days=SESSION_DAYS)))
    db.commit()
    return token,csrf

def session_for_request(db,request):
    token=request.cookies.get('gd_session')
    if not token: return None,None
    sess=db.query(AuthSession).filter(AuthSession.token_hash==digest(token)).first()
    if not sess:return None,None
    expiry=sess.expires_at
    if expiry.tzinfo is None: expiry=expiry.replace(tzinfo=timezone.utc)
    if expiry<=datetime.now(timezone.utc): return None,None
    return db.get(User,sess.user_id),sess

def require_auth(db,request):
    user,sess=session_for_request(db,request)
    if not user: raise HTTPException(status_code=401,detail='Please sign in')
    return user,sess

def require_csrf(request,sess):
    token=request.headers.get('X-CSRF-Token','')
    if not token or not hmac.compare_digest(digest(token),sess.csrf_token_hash):
        raise HTTPException(status_code=403, detail='Invalid CSRF token')

def secure_cookie():return os.getenv('COOKIE_SECURE','false').lower()=='true'

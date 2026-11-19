"""Create or update one *private* account from interactive, non-echoed password input.
The password is NEVER kept in this script, examples or repository.
Run: python -m scripts.bootstrap_user
"""
import getpass
from app.db import init_db,SessionLocal
from app.models import User
from app.security import make_password_hash
from app.services import seed_user_plan

def main():
    init_db()
    email=input('Private login email: ').strip().lower()
    password=getpass.getpass('Password (not displayed): ')
    repeat=getpass.getpass('Repeat password: ')
    if password!=repeat:raise SystemExit('Passwords do not match')
    pwh=make_password_hash(password)
    with SessionLocal() as db:
        user=db.query(User).filter_by(email=email).first()
        if user:
            user.password_hash=pwh
        else:
            user=User(email=email,password_hash=pwh,timezone='Europe/London',cuisine='Indian')
            db.add(user)
        db.commit()
        seed_user_plan(db,user)
    print('Private account and example clinician schedule set up successfully.')
if __name__=='__main__':main()

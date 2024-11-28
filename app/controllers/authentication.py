import bcrypt, pyotp
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
from models.database import Code, User, engine
from controllers.utils import (get_email, 
                               get_email_for_register, 
                               get_input, 
                               get_password, 
                               get_pseudo,
                               get_pseudo_for_register,
                               getpass, 
                               inform, 
                               pause, 
                               send_mail,
                               countdown_timer)


def register():
    with sessionmaker(bind=engine)() as session:
        name = get_input("full name", input)
        pseudo = get_pseudo_for_register()
        email = get_email_for_register()
        password = get_password()
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        user = User(name=name, pseudo=pseudo, email=email, password=password_hash)
        session.add(user)
        session.commit()


def login():
    pseudo = get_pseudo()
    password = get_input("password", getpass)
    with sessionmaker(bind=engine)() as session:
        user = session.query(User).filter_by(pseudo = pseudo).one_or_none()
        if not user:
            inform("wrong pseudo or password")
            exit()
        duration = int(user.delay_end_datetime.timestamp() - datetime.now().timestamp())
        if duration <= 0:
            if user and bcrypt.checkpw(password.encode("utf-8"), user.password):
                user.delay = 0
                user.delay_end_datetime = datetime.now()
                session.commit()
                return (user.id, user.pseudo, user.email)
            else:
                previous_delay = user.delay
                previous_delay += 1
                user.delay = previous_delay
                user.delay_end_datetime = datetime.now() + timedelta(minutes=(5*previous_delay))
                session.commit()
                inform("wrong pseudo or password")
                countdown_timer((previous_delay*5) * 60)
        else:
            countdown_timer(duration)


def MFA_generate(request_user_pseudo):
    with sessionmaker(bind=engine)() as session:
        request_user = session.query(User).filter_by(pseudo = request_user_pseudo).one_or_none()
        totp = pyotp.TOTP(pyotp.random_base32(), interval=300)
        email_code = totp.now()
        code_key = totp.secret
        dead_date = datetime.now() + timedelta(minutes=5)
        send_mail(receiver_mail = request_user.email,
                message_subject = "User Email Verification",
                message_type = "CODE",
                message_body = {
                    "name": request_user.name,
                    "code": email_code
                })
        code = Code(secret_key = code_key, expired_datetime = dead_date, user = request_user)
        session.add(code)
        session.commit()
        inform("a code has been sent to your email box; go check it")


def MFA_verify(request_user_pseudo, request_user_code):
    with sessionmaker(bind=engine)() as session:
        request_user = session.query(User).filter_by(pseudo = request_user_pseudo).one_or_none()
        code = session.query(Code).filter_by(user = request_user).order_by(Code.id.desc()).first()
        if code:
            if datetime.now() <= code.expired_datetime:
                totp = pyotp.TOTP(code.secret_key, interval=300)
                if totp.verify(request_user_code) :
                    code.verified = True
                    session.commit()
                    return "verified"
                else:
                    inform("the given code do not match what we sent to your email box")
            else:
                inform("your OTP code has expired; feel free to ask for another one")
        pause()
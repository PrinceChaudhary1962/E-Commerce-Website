import os
import smtplib
import random
import datetime
from email.message import EmailMessage
from passlib.hash import bcrypt
import qrcode
from io import BytesIO

from models import SessionLocal, OTP

DB = SessionLocal()

# --- Password hashing ---
def hash_password(password: str) -> str:
    return bcrypt.hash(password)

def verify_password(password: str, hash_val: str) -> bool:
    return bcrypt.verify(password, hash_val)

# --- OTP handling ---
def generate_otp_code(length=6):
    return "".join([str(random.randint(0, 9)) for _ in range(length)])

def create_and_send_otp(email):
    code = generate_otp_code()
    expires_at = datetime.datetime.utcnow() + datetime.timedelta(minutes=10)
    # store in DB
    otp = OTP(email=email, code=code, expires_at=expires_at)
    DB.add(otp)
    DB.commit()
    # send email (uses env vars or streamlit secrets)
    send_email(to=email, subject="Your OTP code", body=f"Your OTP code is: {code}\nIt expires in 10 minutes.")
    return code

def verify_otp(email, code):
    now = datetime.datetime.utcnow()
    q = DB.query(OTP).filter(OTP.email == email, OTP.code == code, OTP.expires_at >= now).first()
    if q:
        # delete OTP after use
        DB.delete(q)
        DB.commit()
        return True
    return False

# --- Email sending ---
def send_email(to, subject, body):
    # Reads SMTP settings from env vars: SMTP_USER, SMTP_PASS, SMTP_HOST, SMTP_PORT, FROM_EMAIL
    SMTP_USER = os.environ.get("SMTP_USER")
    SMTP_PASS = os.environ.get("SMTP_PASS")
    SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
    FROM = os.environ.get("FROM_EMAIL", SMTP_USER)

    if not SMTP_USER or not SMTP_PASS:
        print("Warning: SMTP credentials not set. OTP emails will not be sent. Set SMTP_USER and SMTP_PASS.")
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = FROM
    msg["To"] = to
    msg.set_content(body)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)
    return True

# --- UPI QR generation ---
def generate_upi_qr(vpa, name, amount, note="Payment"):
    # simple UPI deep link payload
    # upi://pay?pa=<VPA>&pn=<name>&am=<amount>&tn=<note>
    uri = f"upi://pay?pa={vpa}&pn={name}&am={amount}&tn={note}"
    img = qrcode.make(uri)
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


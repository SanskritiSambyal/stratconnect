"""Institute-email verification and access control.
 
Flow:
  1. Teammate enters their institute email.
  2. We check it is authorized (explicit email grant, an @domain grant, or a
     domain listed in secrets). Unauthorized emails are turned away.
  3. We email a 6-digit one-time code and they type it back to prove ownership.
  4. On success we store their verified email + role in the session.
 
Authorization sources (highest first):
  - secrets["admins"]              -> always 'admin' (bootstrap)
  - access worksheet: exact email  -> its role
  - access worksheet: "@domain"    -> its role
  - secrets["allowed_domains"]     -> secrets["default_role"] (default 'viewer')
"""
import base64
import hashlib
import hmac
import random
import re
import smtplib
import time
from email.mime.text import MIMEText
 
import streamlit as st
 
import storage
from constants import APP_NAME
 
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
OTP_TTL = 600          # seconds a code stays valid
RESEND_GAP = 30        # seconds between sends
MAX_ATTEMPTS = 5
SESSION_HOURS = 8      # how long a verified login stays valid
COOKIE_NAME = "scx_auth"
 
 
def _secret(key, default=None):
    try:
        return st.secrets[key]
    except Exception:
        return default
 
 
def valid_email(email):
    return bool(EMAIL_RE.match((email or "").strip()))
 
 
def resolve_role(email):
    """Return the role for an email, or None if not authorized."""
    email = (email or "").strip().lower()
    if not email:
        return None
    admins = [a.strip().lower() for a in (_secret("admins", []) or [])]
    if email in admins:
        return "admin"
 
    domain = email.split("@")[-1]
    exact, domain_rule = None, None
    try:
        for entry, role in storage.list_access():
            if entry == email:
                exact = role
            elif entry.startswith("@") and entry[1:] == domain:
                domain_rule = role
    except Exception:
        pass
    if exact:
        return exact
    if domain_rule:
        return domain_rule
 
    allowed_domains = [d.strip().lower().lstrip("@") for d in (_secret("allowed_domains", []) or [])]
    if domain in allowed_domains:
        return (_secret("default_role", "viewer") or "viewer").lower()
    return None
 
 
# ------------------------------------------------------------------ OTP helpers
def _salt():
    s = _secret("otp_salt")
    if s:
        return str(s)
    if "_otp_salt" not in st.session_state:
        st.session_state["_otp_salt"] = uuid4_hex()
    return st.session_state["_otp_salt"]
 
 
def uuid4_hex():
    import uuid
    return uuid.uuid4().hex
 
 
def _hash(code):
    return hmac.new(_salt().encode(), str(code).encode(), hashlib.sha256).hexdigest()
 
 
def _brevo_configured():
    cfg = _secret("brevo")
    return bool(cfg and cfg.get("api_key") and cfg.get("sender_email"))
 
 
def _smtp_configured():
    cfg = _secret("smtp")
    return bool(cfg and cfg.get("host") and cfg.get("user") and cfg.get("password"))
 
 
def _delivery_configured():
    return _brevo_configured() or _smtp_configured()
 
 
def send_code(email):
    """Generate, store and email a one-time code. Returns (ok, message, dev_code)."""
    now = time.time()
    last = st.session_state.get("otp_sent_at", 0)
    if now - last < RESEND_GAP:
        wait = int(RESEND_GAP - (now - last))
        return False, f"Please wait {wait}s before requesting another code.", None
 
    code = f"{random.randint(0, 999999):06d}"
    st.session_state["otp_hash"] = _hash(code)
    st.session_state["otp_email"] = email.strip().lower()
    st.session_state["otp_expires"] = now + OTP_TTL
    st.session_state["otp_sent_at"] = now
    st.session_state["otp_attempts"] = 0
 
    subject = f"{APP_NAME}: your sign-in code"
    body = (f"Your {APP_NAME} verification code is:\n\n    {code}\n\n"
            f"It expires in {OTP_TTL // 60} minutes. If you didn't request this, ignore this email.")
 
    if not _delivery_configured():
        if _secret("allow_insecure_dev_login"):
            return True, "Dev mode: email delivery isn't configured, so the code is shown below.", code
        return False, ("Email delivery isn't configured yet. Ask the admin to set the "
                       "[brevo] (or [smtp]) section in secrets."), None
    try:
        _deliver(email, subject, body)
        return True, f"We sent a 6-digit code to {email}. Enter it below.", None
    except Exception as e:
        return False, f"Could not send the email ({e}).", None
 
 
def _deliver(to_email, subject, body):
    """Send via Brevo's HTTPS API if configured (works on Streamlit Cloud),
    otherwise fall back to SMTP."""
    if _brevo_configured():
        _send_via_brevo(to_email, subject, body)
    else:
        _send_via_smtp(to_email, subject, body)
 
 
def _send_via_brevo(to_email, subject, body):
    import requests
    cfg = _secret("brevo")
    resp = requests.post(
        "https://api.brevo.com/v3/smtp/email",
        headers={"api-key": cfg["api_key"], "accept": "application/json",
                 "content-type": "application/json"},
        json={
            "sender": {"name": cfg.get("sender_name", APP_NAME), "email": cfg["sender_email"]},
            "to": [{"email": to_email}],
            "subject": subject,
            "textContent": body,
        },
        timeout=20,
    )
    if resp.status_code >= 300:
        raise RuntimeError(f"Brevo {resp.status_code}: {resp.text[:200]}")
 
 
def _send_via_smtp(to_email, subject, body):
    cfg = _secret("smtp")
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = cfg.get("from", cfg["user"])
    msg["To"] = to_email
    port = int(cfg.get("port", 587))
    host = cfg["host"]
    if port == 465:
        with smtplib.SMTP_SSL(host, port, timeout=20) as s:
            s.login(cfg["user"], cfg["password"])
            s.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=20) as s:
            s.starttls()
            s.login(cfg["user"], cfg["password"])
            s.send_message(msg)
 
 
def verify_code(entered):
    """Check the entered code. Returns (ok, message)."""
    if "otp_hash" not in st.session_state:
        return False, "Request a code first."
    if time.time() > st.session_state.get("otp_expires", 0):
        return False, "That code has expired — request a new one."
    st.session_state["otp_attempts"] = st.session_state.get("otp_attempts", 0) + 1
    if st.session_state["otp_attempts"] > MAX_ATTEMPTS:
        return False, "Too many attempts — request a new code."
    if hmac.compare_digest(_hash((entered or "").strip()), st.session_state["otp_hash"]):
        return True, "Verified."
    return False, "That code doesn't match. Try again."
 
 
# ----------------------------------------------------- signed session token
def make_token(email, exp_ts):
    """A tamper-proof token carrying the email and its expiry."""
    msg = f"{email}|{int(exp_ts)}"
    sig = hmac.new(_salt().encode(), msg.encode(), hashlib.sha256).hexdigest()
    raw = f"{msg}|{sig}".encode()
    return base64.urlsafe_b64encode(raw).decode()
 
 
def read_token(token):
    """Return (email, exp) if the token is valid and unexpired, else (None, None)."""
    try:
        raw = base64.urlsafe_b64decode(token.encode()).decode()
        email, exp, sig = raw.rsplit("|", 2)
        good = hmac.new(_salt().encode(), f"{email}|{exp}".encode(), hashlib.sha256).hexdigest()
        if hmac.compare_digest(good, sig) and time.time() < int(exp):
            return email, int(exp)
    except Exception:
        pass
    return None, None
 
 
def complete_login():
    """Promote a verified OTP email into a signed-in session (valid SESSION_HOURS)."""
    email = st.session_state.get("otp_email")
    role = resolve_role(email)
    if not role:
        return False
    exp = time.time() + SESSION_HOURS * 3600
    st.session_state["auth"] = {"email": email, "role": role, "exp": exp}
    st.session_state["_pending_cookie"] = make_token(email, exp)  # app.py writes the cookie
    for k in ("otp_hash", "otp_email", "otp_expires", "otp_sent_at", "otp_attempts"):
        st.session_state.pop(k, None)
    return True
 
 
def restore_from_token(token):
    """Re-establish a session from a valid cookie token (used on page reload)."""
    email, exp = read_token(token)
    if not email:
        return False
    role = resolve_role(email)
    if not role:
        return False
    st.session_state["auth"] = {"email": email, "role": role, "exp": exp}
    return True
 
 
def current_user():
    a = st.session_state.get("auth")
    if a and a.get("exp", 0) > time.time():
        return a
    if a:  # expired — drop it and clear the cookie
        st.session_state.pop("auth", None)
        st.session_state["_clear_cookie"] = True
    return None
 
 
def logout():
    for k in ("auth", "otp_hash", "otp_email", "otp_expires", "otp_sent_at",
              "otp_attempts", "editing_id", "page"):
        st.session_state.pop(k, None)
    st.session_state["_clear_cookie"] = True  # app.py deletes the cookie
 

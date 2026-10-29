"""Email + one-time-code gate for the hosted demo.

A student enters an @iitr.ac.in address, receives a 6-digit code by email
(Gmail SMTP) and enters it to unlock the dashboard.

The logic works on a plain `state` dict (pending codes, send log, lock) rather
than on a class, because app.py drops this project's modules from sys.modules
on every run; the dict lives in st.cache_resource and so survives that, while
the functions below are re-imported freely.

Secrets (Streamlit Cloud "Secrets" panel, or .streamlit/secrets.toml locally):

    [auth]
    smtp_user = "yourdemoaccount@gmail.com"
    smtp_password = "<16-character Gmail app password>"
    # optional: allowed_domain = "iitr.ac.in"

Setting the environment variable AUTH_DISABLED=1 skips the gate (tests, local use).
"""

import hashlib
import hmac
import os
import re
import secrets
import smtplib
import threading
import time
from email.message import EmailMessage

import streamlit as st

ALLOWED_DOMAIN = "iitr.ac.in"
OTP_DIGITS = 6
OTP_TTL_SECONDS = 5 * 60
MAX_ATTEMPTS = 5
RESEND_COOLDOWN_SECONDS = 60
MAX_SENDS_PER_HOUR = 5

_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+)$")


def new_state() -> dict:
    return {"lock": threading.Lock(), "pending": {}, "sent": {}}


def normalize_email(raw: str) -> str:
    return (raw or "").strip().lower()


def is_allowed_email(email: str, domain: str = ALLOWED_DOMAIN) -> bool:
    """True for name@domain and name@anything.domain (e.g. name@ce.iitr.ac.in)."""
    match = _EMAIL_RE.match(email)
    if not match:
        return False
    host = match.group(1)
    return host == domain or host.endswith("." + domain)


def _hash(code: str, salt: str) -> str:
    return hashlib.sha256((salt + code).encode()).hexdigest()


def issue_code(state: dict, email: str, send, now: float = None) -> tuple[bool, str]:
    """Create and email a code. `send(email, code)` does the delivery.
    Returns (ok, message)."""
    now = time.time() if now is None else now
    with state["lock"]:
        recent = [t for t in state["sent"].get(email, []) if now - t < 3600]
        if recent and now - recent[-1] < RESEND_COOLDOWN_SECONDS:
            wait = int(RESEND_COOLDOWN_SECONDS - (now - recent[-1])) + 1
            return False, f"Please wait {wait} s before asking for another code."
        if len(recent) >= MAX_SENDS_PER_HOUR:
            return False, "Too many codes requested for this address. Try again in an hour."

        code = "".join(str(secrets.randbelow(10)) for _ in range(OTP_DIGITS))
        salt = secrets.token_hex(8)
        try:
            send(email, code)
        except Exception:
            return False, "Could not send the email. Please try again shortly."

        state["sent"][email] = recent + [now]
        state["pending"][email] = {
            "salt": salt, "hash": _hash(code, salt),
            "expires": now + OTP_TTL_SECONDS, "attempts": 0,
        }
    return True, f"A {OTP_DIGITS}-digit code was sent to {email}."


def check_code(state: dict, email: str, code: str, now: float = None) -> tuple[bool, str]:
    """Verify a submitted code. A code is single-use. Returns (ok, message)."""
    now = time.time() if now is None else now
    code = (code or "").strip()
    with state["lock"]:
        entry = state["pending"].get(email)
        if entry is None:
            return False, "No code is pending for this address. Request a new one."
        if now > entry["expires"]:
            del state["pending"][email]
            return False, "That code has expired. Request a new one."
        entry["attempts"] += 1
        if hmac.compare_digest(_hash(code, entry["salt"]), entry["hash"]):
            del state["pending"][email]
            return True, "Verified."
        if entry["attempts"] >= MAX_ATTEMPTS:
            del state["pending"][email]
            return False, "Too many wrong attempts. Request a new code."
        left = MAX_ATTEMPTS - entry["attempts"]
        return False, f"Incorrect code. {left} attempt(s) left."


def smtp_sender(user: str, password: str):
    """Return send(email, code) that delivers through Gmail SMTP over SSL."""
    def send(email: str, code: str) -> None:
        msg = EmailMessage()
        msg["Subject"] = "Your Opti-Money demo verification code"
        msg["From"] = user
        msg["To"] = email
        msg.set_content(
            f"Your verification code is {code}\n\n"
            f"It expires in {OTP_TTL_SECONDS // 60} minutes. "
            "If you did not request it, ignore this email."
        )
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as server:
            server.login(user, password)
            server.send_message(msg)
    return send


@st.cache_resource
def _shared_state() -> dict:
    return new_state()


def _auth_secrets() -> dict:
    try:
        return dict(st.secrets["auth"])
    except Exception:
        return {}


def require_login() -> bool:
    """Show the email/code screens until the visitor is verified.
    Returns True once verified (or if the gate is disabled)."""
    if os.environ.get("AUTH_DISABLED") == "1":
        return True
    if st.session_state.get("verified_email"):
        return True

    cfg = _auth_secrets()
    if not cfg.get("smtp_user") or not cfg.get("smtp_password"):
        st.error("Sign-in is not configured on this server (missing SMTP secrets).")
        return False

    domain = cfg.get("allowed_domain", ALLOWED_DOMAIN)
    state = _shared_state()
    send = smtp_sender(cfg["smtp_user"], cfg["smtp_password"])

    st.title("Opti-Money CRM demo")
    st.write(f"Sign in with your @{domain} email address. We will send you a one-time code.")

    pending_email = st.session_state.get("auth_pending_email")

    if not pending_email:
        with st.form("auth_email_form"):
            raw = st.text_input("College email", placeholder=f"name@{domain}")
            submitted = st.form_submit_button("Send code")
        if submitted:
            email = normalize_email(raw)
            if not is_allowed_email(email, domain):
                st.error(f"Please use a valid @{domain} email address.")
            else:
                ok, message = issue_code(state, email, send)
                if ok:
                    st.session_state["auth_pending_email"] = email
                    st.rerun()
                else:
                    st.error(message)
        return False

    st.info(f"A code was sent to {pending_email}. It is valid for {OTP_TTL_SECONDS // 60} minutes.")
    with st.form("auth_code_form"):
        code = st.text_input("6-digit code", max_chars=OTP_DIGITS)
        submitted = st.form_submit_button("Verify")
    if submitted:
        ok, message = check_code(state, pending_email, code)
        if ok:
            st.session_state["verified_email"] = pending_email
            st.session_state.pop("auth_pending_email", None)
            st.rerun()
        else:
            st.error(message)

    left, right = st.columns(2)
    if left.button("Resend code"):
        ok, message = issue_code(state, pending_email, send)
        (st.success if ok else st.error)(message)
    if right.button("Use a different email"):
        st.session_state.pop("auth_pending_email", None)
        st.rerun()
    return False

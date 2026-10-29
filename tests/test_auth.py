"""Tests for the email + one-time-code gate (src/auth.py). No real email is sent."""

import os
import sys

import pytest
from streamlit.testing.v1 import AppTest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "src"))
import auth

APP = os.path.join(ROOT, "src", "app.py")


class Outbox:
    """Fake sender that records the codes it was asked to deliver."""
    def __init__(self, fail=False):
        self.sent, self.fail = [], fail

    def __call__(self, email, code):
        if self.fail:
            raise OSError("smtp down")
        self.sent.append((email, code))


EMAIL = "student_ab@ce.iitr.ac.in"


def test_allowed_emails():
    assert auth.is_allowed_email("a@iitr.ac.in")
    assert auth.is_allowed_email(EMAIL)
    for bad in ["a@gmail.com", "a@iitr.ac.in.evil.com", "a@eviitr.ac.in",
                "iitr.ac.in", "a b@iitr.ac.in", "a@@iitr.ac.in", ""]:
        assert not auth.is_allowed_email(bad), bad


def test_correct_code_verifies_once():
    state, box = auth.new_state(), Outbox()
    ok, _ = auth.issue_code(state, EMAIL, box, now=0)
    assert ok
    code = box.sent[0][1]
    assert len(code) == 6 and code.isdigit()
    assert auth.check_code(state, EMAIL, code, now=10)[0]
    assert not auth.check_code(state, EMAIL, code, now=11)[0]   # single use


def test_wrong_code_then_lockout():
    state, box = auth.new_state(), Outbox()
    auth.issue_code(state, EMAIL, box, now=0)
    real = box.sent[0][1]
    wrong = "000000" if real != "000000" else "111111"
    for _ in range(auth.MAX_ATTEMPTS):
        assert not auth.check_code(state, EMAIL, wrong, now=5)[0]
    assert not auth.check_code(state, EMAIL, real, now=6)[0]    # locked out


def test_code_expires():
    state, box = auth.new_state(), Outbox()
    auth.issue_code(state, EMAIL, box, now=0)
    code = box.sent[0][1]
    ok, msg = auth.check_code(state, EMAIL, code, now=auth.OTP_TTL_SECONDS + 1)
    assert not ok and "expired" in msg


def test_resend_cooldown_and_hourly_cap():
    state, box = auth.new_state(), Outbox()
    assert auth.issue_code(state, EMAIL, box, now=0)[0]
    assert not auth.issue_code(state, EMAIL, box, now=10)[0]    # too soon
    t = 0
    for _ in range(auth.MAX_SENDS_PER_HOUR - 1):
        t += auth.RESEND_COOLDOWN_SECONDS + 1
        assert auth.issue_code(state, EMAIL, box, now=t)[0]
    t += auth.RESEND_COOLDOWN_SECONDS + 1
    ok, msg = auth.issue_code(state, EMAIL, box, now=t)
    assert not ok and "hour" in msg
    assert auth.issue_code(state, EMAIL, box, now=3601)[0]      # window slides


def test_new_code_replaces_old_one():
    state, box = auth.new_state(), Outbox()
    auth.issue_code(state, EMAIL, box, now=0)
    auth.issue_code(state, EMAIL, box, now=100)
    first, second = box.sent[0][1], box.sent[1][1]
    if first != second:
        assert not auth.check_code(state, EMAIL, first, now=101)[0]


def test_send_failure_stores_nothing():
    state = auth.new_state()
    ok, _ = auth.issue_code(state, EMAIL, Outbox(fail=True), now=0)
    assert not ok and EMAIL not in state["pending"] and EMAIL not in state["sent"]


def test_gate_blocks_dashboard_without_secrets(monkeypatch):
    monkeypatch.delenv("AUTH_DISABLED", raising=False)
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    assert not at.exception
    assert any("not configured" in e.value for e in at.error)
    assert not at.tabs          # dashboard did not render


def test_gate_shows_email_form_and_rejects_other_domains(monkeypatch):
    monkeypatch.delenv("AUTH_DISABLED", raising=False)
    at = AppTest.from_file(APP, default_timeout=60)
    at.secrets["auth"] = {"smtp_user": "x@gmail.com", "smtp_password": "pw"}
    at.run()
    assert not at.exception
    at.text_input[0].set_value("someone@gmail.com")
    at.button[0].click()
    at.run()
    assert any("@iitr.ac.in" in e.value for e in at.error)
    assert not at.tabs


def test_verified_session_reaches_dashboard(monkeypatch):
    monkeypatch.delenv("AUTH_DISABLED", raising=False)
    at = AppTest.from_file(APP, default_timeout=90)
    at.session_state["verified_email"] = EMAIL
    at.run()
    assert not at.exception
    assert len(at.tabs) == 4

"""Existing dashboard tests run with the email sign-in gate switched off;
tests/test_auth.py turns it back on where it needs it."""

import os

os.environ["AUTH_DISABLED"] = "1"

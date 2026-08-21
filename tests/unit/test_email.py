"""Email: free-фоллбек в outbox, когда SMTP не настроен."""
import pytest

from app import email as email_mod
from app.email import send_email, verification_email

pytestmark = pytest.mark.unit


def test_outbox_fallback_when_no_smtp(tmp_path, monkeypatch):
    # SMTP не настроен → письмо пишется в outbox и возвращается True.
    monkeypatch.setattr(email_mod.settings, "email_host", "", raising=False)
    monkeypatch.setattr(email_mod, "_OUTBOX", tmp_path / "outbox")
    ok = send_email("user@test.local", "Subject", "Body text")
    assert ok is True
    files = list((tmp_path / "outbox").glob("*.txt"))
    assert len(files) == 1
    content = files[0].read_text(encoding="utf-8")
    assert "user@test.local" in content
    assert "Body text" in content


def test_verification_email_text_has_link():
    subject, body = verification_email("Jānis", "https://x/verificet?token=abc", "App")
    assert "App" in subject
    assert "https://x/verificet?token=abc" in body
    assert "Jānis" in body

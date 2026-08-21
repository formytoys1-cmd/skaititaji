"""Anti-bot: honeypot + подписанная метка времени (free, без сервисов)."""
import time

import pytest

from app.antibot import (
    MIN_SECONDS,
    check_human,
    make_timestamp_token,
)

pytestmark = pytest.mark.unit


def test_honeypot_filled_is_bot():
    ts = make_timestamp_token(now=time.time() - 5)
    assert check_human("i-am-a-bot", ts) is False


def test_valid_human_passes():
    ts = make_timestamp_token(now=time.time() - (MIN_SECONDS + 1))
    assert check_human("", ts) is True


def test_too_fast_is_bot():
    ts = make_timestamp_token()  # свежая метка, возраст ~0 < MIN_SECONDS
    assert check_human("", ts) is False


def test_missing_timestamp_is_bot():
    assert check_human("", "") is False
    assert check_human("", None) is False


def test_tampered_signature_is_bot():
    ts = make_timestamp_token(now=time.time() - 5)
    stamp, _sig = ts.split(".", 1)
    forged = f"{stamp}.deadbeef"
    assert check_human("", forged) is False


def test_expired_timestamp_is_bot():
    ts = make_timestamp_token(now=time.time() - 7200)  # 2 часа назад > MAX
    assert check_human("", ts) is False

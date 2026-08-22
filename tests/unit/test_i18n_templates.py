"""Гард против регресса i18n: в шаблонах не должно быть жёстко зашитого
латышского текста (со спецбуквами āčēž…) вне вызовов t().

Почему именно LV-спецбуквы: они однозначно указывают на непереведённую строку.
Английский/русский текст так надёжно не отличить от кода, поэтому проверяем
самый частый источник «халтуры» — прямой латышский в разметке.
"""
import glob
import re

import pytest

pytestmark = pytest.mark.unit

LV_CHARS = set("āčēģīķļņōŗšūžĀČĒĢĪĶĻŅŌŖŠŪŽ")
TAG_TEXT = re.compile(
    r'>([^<>{}]*[A-Za-zĀČĒĢĪĶĻŅŌŖŠŪŽāčēģīķļņōŗšūž][^<>{}]*)<'
)

# Разрешённые исключения: бренды/имена собственные и т.п., которые не переводятся.
WHITELIST = {"Smart-ID", "eParaksts", "Internetbanka"}


def _hardcoded_lv(path: str) -> list[str]:
    text = open(path, encoding="utf-8").read()
    hits = []
    for m in TAG_TEXT.finditer(text):
        s = m.group(1).strip()
        if not s or s in WHITELIST:
            continue
        if s.startswith("{{") or s.startswith("{%"):
            continue
        if any(c in LV_CHARS for c in s):
            hits.append(s)
    return hits


def test_no_hardcoded_latvian_in_templates():
    offenders = {}
    for path in glob.glob("app/templates/**/*.html", recursive=True):
        hits = _hardcoded_lv(path)
        if hits:
            offenders[path] = hits
    assert not offenders, (
        "Жёстко зашитый латышский текст вне t() (используйте ключи i18n):\n"
        + "\n".join(f"  {p}: {h}" for p, h in offenders.items())
    )

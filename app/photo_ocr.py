"""OCR helpers for meter photos."""
from __future__ import annotations

import re
from dataclasses import dataclass

import httpx

from app.config import settings

OCR_SPACE_URL = "https://api.ocr.space/parse/image"
OCR_DEMO_KEY = "helloworld"
NUM_RE = re.compile(r"\d{1,8}(?:[.,]\d{1,3})?")


class PhotoOCRError(Exception):
    """Raised when OCR provider is unavailable or returns an error."""


@dataclass(frozen=True)
class PhotoOCRResult:
    value: float | None
    candidates: list[float]
    raw_text: str
    provider: str
    warning: str | None = None


def extract_numeric_candidates(text: str) -> list[float]:
    """Extracts possible meter values from OCR text."""
    values: list[float] = []
    seen: set[float] = set()
    for token in NUM_RE.findall(text):
        normalized = token.replace(",", ".")
        try:
            value = round(float(normalized), 3)
        except ValueError:
            continue
        if value < 0 or value > 1_000_000:
            continue
        if value in seen:
            continue
        seen.add(value)
        values.append(value)
    return values


def pick_best_candidate(candidates: list[float]) -> float | None:
    """Picks the most plausible value from OCR candidates."""
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda value: (len(str(int(value))), value),
    )


def _extract_text_from_ocr_space(payload: dict) -> str:
    parsed = payload.get("ParsedResults")
    if not isinstance(parsed, list):
        return ""
    lines: list[str] = []
    for item in parsed:
        if isinstance(item, dict):
            text = item.get("ParsedText")
            if isinstance(text, str):
                lines.append(text)
    return "\n".join(lines).strip()


def _ocr_api_key() -> str:
    key = getattr(settings, "ocr_space_api_key", "").strip()
    if key:
        return key
    if getattr(settings, "ocr_space_allow_demo_key", False):
        return OCR_DEMO_KEY
    return ""


async def recognize_meter_photo(
    *, filename: str, data: bytes, content_type: str
) -> PhotoOCRResult:
    """Recognizes probable meter value from an uploaded photo."""
    api_key = _ocr_api_key()
    if not api_key:
        raise PhotoOCRError(
            "OCR is not configured. Set OCR_SPACE_API_KEY or enable OCR_SPACE_ALLOW_DEMO_KEY=1."
        )

    payload = {
        "apikey": api_key,
        "language": "eng",
        "OCREngine": "2",
        "scale": "true",
        "isOverlayRequired": "false",
    }
    files = {"file": (filename, data, content_type)}

    timeout = float(getattr(settings, "ocr_space_timeout_sec", 20))
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(OCR_SPACE_URL, data=payload, files=files)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise PhotoOCRError(f"OCR provider request failed: {exc}") from exc

    body = response.json()
    if body.get("IsErroredOnProcessing"):
        err = body.get("ErrorMessage") or body.get("ErrorDetails") or "OCR failed"
        if isinstance(err, list):
            err = "; ".join(str(x) for x in err)
        raise PhotoOCRError(str(err))

    raw_text = _extract_text_from_ocr_space(body)
    candidates = extract_numeric_candidates(raw_text)
    best = pick_best_candidate(candidates)
    warning = None
    if best is None:
        warning = "Could not confidently detect numeric reading. Please enter manually."
    return PhotoOCRResult(
        value=best,
        candidates=candidates[:5],
        raw_text=raw_text[:1000],
        provider="ocr.space",
        warning=warning,
    )

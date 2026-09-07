import pytest

from app.photo_ocr import extract_numeric_candidates, pick_best_candidate

pytestmark = pytest.mark.unit


def test_extract_numeric_candidates_parses_common_formats():
    text = "HVS 00123,456 GVS 98.7 serija 99999999"
    candidates = extract_numeric_candidates(text)
    assert 123.456 in candidates
    assert 98.7 in candidates


def test_pick_best_candidate_prefers_most_plausible_max():
    candidates = [12.3, 456.0, 45.67]
    assert pick_best_candidate(candidates) == 456.0
    assert pick_best_candidate([]) is None

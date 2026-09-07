import re

import pytest
from sqlmodel import Session, select

from app.models import Meter, Reading, UnitResident, User
from app.photo_ocr import PhotoOCRResult

pytestmark = pytest.mark.integration


def _csrf(client) -> str:
    html = client.get("/login").text
    return re.search(r'name="csrf_token"\s+value="([^"]+)"', html).group(1)


def _login_resident(client, csrf):
    return client.post(
        "/login",
        data={"email": "resident@demo.lv", "password": "demo1234", "csrf_token": csrf},
        follow_redirects=False,
    )


def test_photo_recognition_confirm_saves_reading(client, engine, monkeypatch):
    csrf = _csrf(client)
    _login_resident(client, csrf)

    async def _fake_ocr(*, filename: str, data: bytes, content_type: str):
        return PhotoOCRResult(
            value=222.123,
            candidates=[222.123],
            raw_text="222.123",
            provider="test",
            warning=None,
        )

    monkeypatch.setattr("app.routers.resident.recognize_meter_photo", _fake_ocr)

    recognize = client.post(
        "/dzivoklis/photo/recognize",
        data={"csrf_token": csrf},
        files=[("photos", ("meter.jpg", b"fake-image", "image/jpeg"))],
    )
    assert recognize.status_code == 200
    assert "photo/confirm" in recognize.text

    with Session(engine) as session:
        resident = session.exec(
            select(User).where(User.email == "resident@demo.lv")
        ).first()
        assert resident is not None
        unit_link = session.exec(
            select(UnitResident).where(UnitResident.user_id == resident.id)
        ).first()
        assert unit_link is not None
        meter = session.exec(select(Meter).where(Meter.unit_id == unit_link.unit_id)).first()
        assert meter is not None

    confirm = client.post(
        "/dzivoklis/photo/confirm",
        data={
            "csrf_token": csrf,
            "row_ids": "0",
            "confirm_0": "1",
            "meter_0": str(meter.id),
            "value_0": "222.123",
        },
        follow_redirects=False,
    )
    assert confirm.status_code == 303

    with Session(engine) as session:
        reading = session.exec(
            select(Reading).where(
                Reading.meter_id == meter.id,
                Reading.value == 222.123,
            )
        ).first()
        assert reading is not None

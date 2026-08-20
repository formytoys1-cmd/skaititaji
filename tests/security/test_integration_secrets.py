"""SEC-003: секреты интеграции Visma шифруются at-rest и маскируются в UI."""
import pytest

from app.models import UserRole

pytestmark = pytest.mark.security


def test_integration_secret_encrypted_at_rest(session, factory):
    from app.integrations.config import set_integration_secret
    from app.secrets_crypto import is_encrypted

    org = factory.organization()
    set_integration_secret(org, "password", "s3cr3t-horizon")
    session.add(org)
    session.commit()
    session.refresh(org)

    stored = org.integration_config.get("password_enc")
    # Открытого пароля в конфиге быть не должно.
    assert "password" not in org.integration_config or org.integration_config.get("password") != "s3cr3t-horizon"
    assert stored is not None
    assert is_encrypted(stored)
    assert "s3cr3t-horizon" not in str(org.integration_config)

    # И его можно корректно расшифровать обратно.
    from app.integrations.config import get_integration_secret
    assert get_integration_secret(org, "password") == "s3cr3t-horizon"


def test_secret_masked_in_admin_view(client, session, factory):
    from app.integrations.config import set_integration_secret

    # Организация с настоящим секретом
    org = factory.organization(name="MaskOrg")
    set_integration_secret(org, "password", "top-secret-pw")
    org.integration_config = {**org.integration_config, "mock": False}
    session.add(org)
    session.commit()

    factory.user(role=UserRole.SUPERADMIN, email="root@test.local",
                 password="pw-abcdef")
    import re
    html = client.get("/login").text
    token = re.search(r'name="csrf_token"\s+value="([^"]+)"', html).group(1)
    client.post("/login", data={"email": "root@test.local", "password": "pw-abcdef",
                "csrf_token": token})

    r = client.get("/admin")
    assert r.status_code == 200
    assert "top-secret-pw" not in r.text


def test_crypto_roundtrip_and_tamper_detection():
    from app.secrets_crypto import decrypt, encrypt, is_encrypted

    token = encrypt("horizon-pw-42")
    assert is_encrypted(token)
    assert "horizon-pw-42" not in token
    assert decrypt(token) == "horizon-pw-42"

    # Подделка ciphertext должна отклоняться MAC-проверкой.
    tampered = token[:-2] + ("AA" if not token.endswith("AA") else "BB")
    with pytest.raises(ValueError):
        decrypt(tampered)


def test_prod_requires_encryption_key(monkeypatch):
    """Boot-guard в проде требует SECRETS_ENCRYPTION_KEY (SEC-003)."""
    from app.config import Settings, validate_production_config

    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("SECRET_KEY", "x" * 40)
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h/db")
    monkeypatch.setenv("ALLOW_DEMO_LOGIN", "0")
    monkeypatch.setenv("DEBUG", "0")
    monkeypatch.delenv("SECRETS_ENCRYPTION_KEY", raising=False)

    cfg = Settings()
    with pytest.raises(RuntimeError) as exc:
        validate_production_config(cfg)
    assert "SECRETS_ENCRYPTION_KEY" in str(exc.value)

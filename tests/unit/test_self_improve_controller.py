"""Тесты самоулучшающегося контролёра на синтетике (без реального git/pytest).

Сценарии мандата:
  - baseline-red => abort (правки не вносятся);
  - safe-apply остаётся (ruff-autofix применён);
  - unsafe => revert (регрессия откатывается через git restore);
  - предложения для рискованного пишутся в docs/self_improve/.
"""
from __future__ import annotations

import datetime as _dt

import tools.self_improve_controller as sic
from tools.self_improve_controller import CmdResult, run_controller


class FakeRunner:
    """Инъектируемый раннер: детерминированные ответы по префиксу команды."""

    def __init__(self, *, pytest_ok=True, ruff_fixed=False, ruff_ok=True,
                 pytest_after_fix_ok=True, coverage_total=95):
        self.pytest_ok = pytest_ok
        self.ruff_fixed = ruff_fixed
        self.ruff_ok = ruff_ok
        self.pytest_after_fix_ok = pytest_after_fix_ok
        self.coverage_total = coverage_total
        self.calls: list[list[str]] = []
        self._pytest_calls = 0

    def __call__(self, cmd):
        cmd = list(cmd)
        self.calls.append(cmd)
        joined = " ".join(cmd)

        if cmd[:2] == ["ruff", "check"] and "--fix" in cmd:
            out = "Fixed 2 errors" if self.ruff_fixed else "No fixes"
            return CmdResult(0, out)
        if cmd[:2] == ["ruff", "check"]:
            return CmdResult(0 if self.ruff_ok else 1, "ruff out")
        if "--cov=app.auth" in joined:
            return CmdResult(0, f"TOTAL 100 5 {self.coverage_total}%\n")
        if "pytest" in joined:
            self._pytest_calls += 1
            # 1-й pytest = baseline; последующие (после fix) = verify
            if self._pytest_calls == 1:
                return CmdResult(0 if self.pytest_ok else 1, "baseline pytest")
            return CmdResult(0 if self.pytest_after_fix_ok else 1, "verify pytest")
        if cmd[:2] == ["git", "restore"]:
            return CmdResult(0, "restored")
        return CmdResult(0, "")


NOW = _dt.datetime(2026, 3, 1, 4, 0, tzinfo=_dt.timezone.utc)


def _run(runner):
    return run_controller(runner=runner, now=NOW, write_side_effects=False)


def test_baseline_red_aborts_without_changes():
    runner = FakeRunner(pytest_ok=False)
    res = _run(runner)
    assert res.aborted is True
    assert "baseline-red" in res.abort_reason
    # ни self-dev, ни handoff не выполнялись — нет git restore и нет ruff --fix
    assert not any("--fix" in c for c in runner.calls)
    assert not any(c[:2] == ["git", "restore"] for c in runner.calls)
    assert res.safe_applied == []


def test_safe_apply_stays_when_verify_green():
    runner = FakeRunner(ruff_fixed=True, pytest_after_fix_ok=True)
    res = _run(runner)
    assert res.aborted is False
    assert "ruff-autofix" in res.self_dev_applied
    assert res.self_dev_reverted == []
    # правка не откатывалась
    assert not any(c[:2] == ["git", "restore"] for c in runner.calls)
    assert any("ruff-autofix" in s for s in res.safe_applied)


def test_unsafe_change_is_reverted():
    runner = FakeRunner(ruff_fixed=True, pytest_after_fix_ok=False)
    res = _run(runner)
    assert res.aborted is False
    assert "ruff-autofix" in res.self_dev_reverted
    assert "ruff-autofix" not in res.self_dev_applied
    # авто-revert выполнен
    assert any(c[:2] == ["git", "restore"] for c in runner.calls)


def test_proposals_written_for_risky(tmp_path, monkeypatch):
    monkeypatch.setattr(sic, "PROPOSALS_DIR", tmp_path)
    runner = FakeRunner(coverage_total=50)  # ниже порога => предложение
    res = _run(runner)
    assert res.proposals, "должно быть хотя бы одно рискованное предложение"
    assert res.proposals_path
    written = (tmp_path / "proposals_2026-03.md").read_text(encoding="utf-8")
    assert "50%" in written
    assert "Требуют решения человека" in written


def test_heartbeat_written(tmp_path, monkeypatch):
    monkeypatch.setattr(sic, "STATE_DIR", tmp_path)
    monkeypatch.setattr(sic, "HEARTBEAT_FILE", tmp_path / "heartbeat.json")
    monkeypatch.setattr(sic, "JOURNAL_FILE", tmp_path / "journal.jsonl")
    runner = FakeRunner()
    res = run_controller(runner=runner, now=NOW, write_side_effects=True)
    assert (tmp_path / "heartbeat.json").exists()
    assert (tmp_path / "journal.jsonl").exists()
    assert res.heartbeat_path


def test_capabilities_registry_loads():
    caps = sic.load_capabilities()
    ids = {c["id"] for c in caps["capabilities"]}
    assert "pytest-green" in ids
    assert "coverage-key-modules" in ids


def test_idempotent_no_changes_when_clean():
    """Идемпотентность: чистый прогон без фиксов не оставляет self-dev правок."""
    runner = FakeRunner(ruff_fixed=False)
    res = _run(runner)
    assert res.self_dev_applied == []
    assert res.self_dev_reverted == []
    assert not any(c[:2] == ["git", "restore"] for c in runner.calls)

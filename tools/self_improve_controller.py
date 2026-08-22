"""Самоулучшающийся контролёр проекта Skaitītāji (месячный автономный цикл).

Детерминированный «мозг» БЕЗ вызова LLM — бесплатный и headless. Запускается раз
в месяц через GitHub Actions (schedule cron), см. .github/workflows/self-improve.yml.

Фазы:
  PRE      — snapshot baseline-гейтов (pytest, покрытие, ruff). baseline-red => abort.
  SELF-DEV — детерминированно улучшить сам контролёр/окружение; при регрессии авто-revert.
  DERIVE   — выделить, что применимо к проекту.
  HANDOFF  — безопасные обратимые правки применить (с бэкапом/откатом); рискованные —
             в очередь предложений docs/self_improve/proposals_YYYY-MM.md для человека.
  POST     — журнал + heartbeat-маркер + отчёт.

Свойства: safe-on-failure (baseline-red => abort), авто-revert небезопасных правок,
идемпотентность, не раскрывать секреты. Всё детерминировано и обратимо.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
CAPABILITIES_FILE = REPO_ROOT / "tools" / "self_improve" / "capabilities.json"
STATE_DIR = REPO_ROOT / "data" / "self_improve"
HEARTBEAT_FILE = STATE_DIR / "heartbeat.json"
JOURNAL_FILE = STATE_DIR / "journal.jsonl"
PROPOSALS_DIR = REPO_ROOT / "docs" / "self_improve"

# Тип раннера команд — инъектируется в тестах (синтетика), в реальности = subprocess.
Runner = Callable[[Sequence[str]], "CmdResult"]


@dataclass
class CmdResult:
    code: int
    out: str = ""

    @property
    def ok(self) -> bool:
        return self.code == 0


def _real_runner(cmd: Sequence[str]) -> CmdResult:
    proc = subprocess.run(
        list(cmd), cwd=str(REPO_ROOT), capture_output=True, text=True
    )
    return CmdResult(code=proc.returncode, out=(proc.stdout or "") + (proc.stderr or ""))


@dataclass
class GateResult:
    name: str
    ok: bool
    detail: str = ""


@dataclass
class ControllerResult:
    aborted: bool = False
    abort_reason: str = ""
    baseline: list[GateResult] = field(default_factory=list)
    self_dev_applied: list[str] = field(default_factory=list)
    self_dev_reverted: list[str] = field(default_factory=list)
    safe_applied: list[str] = field(default_factory=list)
    proposals: list[str] = field(default_factory=list)
    proposals_path: str = ""
    heartbeat_path: str = ""

    def to_dict(self) -> dict:
        return {
            "aborted": self.aborted,
            "abort_reason": self.abort_reason,
            "baseline": [g.__dict__ for g in self.baseline],
            "self_dev_applied": self.self_dev_applied,
            "self_dev_reverted": self.self_dev_reverted,
            "safe_applied": self.safe_applied,
            "proposals": self.proposals,
            "proposals_path": self.proposals_path,
            "heartbeat_path": self.heartbeat_path,
        }


def load_capabilities(path: Path = CAPABILITIES_FILE) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# PRE: baseline-гейты
# --------------------------------------------------------------------------- #
def run_baseline(runner: Runner) -> list[GateResult]:
    """Snapshot текущего здоровья проекта. Порядок: pytest (критично) → ruff."""
    gates: list[GateResult] = []

    pytest_res = runner(
        ["python", "-m", "pytest", "tests/unit", "tests/integration", "-q"]
    )
    gates.append(
        GateResult(
            "pytest",
            pytest_res.ok,
            detail=pytest_res.out[-2000:] if not pytest_res.ok else "ok",
        )
    )

    ruff_res = runner(["ruff", "check", "app", "tests"])
    gates.append(
        GateResult(
            "ruff", ruff_res.ok, detail=ruff_res.out[-2000:] if not ruff_res.ok else "ok"
        )
    )
    return gates


def baseline_is_red(gates: list[GateResult]) -> bool:
    """Baseline красный, если упал критичный гейт pytest."""
    for g in gates:
        if g.name == "pytest" and not g.ok:
            return True
    return False


# --------------------------------------------------------------------------- #
# SELF-DEV: улучшить сам контролёр/окружение с авто-revert
# --------------------------------------------------------------------------- #
def self_dev(runner: Runner, result: ControllerResult) -> None:
    """Безопасные детерминированные улучшения самого контролёра.

    Стратегия: применить обратимую правку (ruff --fix), проверить гейты; если
    краснеют — АВТО-REVERT через `git restore`, никогда не оставлять сломанным.
    """
    fix = runner(["ruff", "check", "--fix", "app", "tests"])
    # Проверяем, что после fix ничего не сломалось.
    verify = runner(["python", "-m", "pytest", "tests/unit", "-q"])
    if verify.ok:
        if fix.out and "fixed" in fix.out.lower():
            result.self_dev_applied.append("ruff-autofix")
    else:
        # регрессия — откатываем всё рабочее дерево
        runner(["git", "restore", "--worktree", "."])
        result.self_dev_reverted.append("ruff-autofix")


# --------------------------------------------------------------------------- #
# DERIVE + HANDOFF
# --------------------------------------------------------------------------- #
def _scheduled_workflows_missing_dispatch() -> list[str]:
    """Детерминированная проверка: у каких workflow есть schedule, но нет dispatch."""
    wf_dir = REPO_ROOT / ".github" / "workflows"
    missing: list[str] = []
    if not wf_dir.exists():
        return missing
    for wf in sorted(wf_dir.glob("*.yml")):
        text = wf.read_text(encoding="utf-8")
        if "schedule:" in text and "workflow_dispatch" not in text:
            missing.append(wf.name)
    return missing


def derive_and_handoff(runner: Runner, result: ControllerResult, month: str) -> None:
    """DERIVE применимое к проекту; HANDOFF: безопасное — применить, рискованное — в очередь."""
    caps = load_capabilities()
    safe_changes: list[str] = []
    risky_proposals: list[str] = []

    # Безопасная обратимая правка: ruff --fix уже применён к рабочему дереву в self_dev;
    # если что-то реально пофикшено — это применимо к проекту.
    if "ruff-autofix" in result.self_dev_applied:
        safe_changes.append(
            "ruff-autofix: применены безопасные авто-исправления линтера (обратимо через git)."
        )

    # Рискованное/требующее решения человека — только предложения.
    missing = _scheduled_workflows_missing_dispatch()
    for wf in missing:
        risky_proposals.append(
            f"Workflow `{wf}` имеет schedule, но не имеет workflow_dispatch — добавить ручной запуск."
        )

    cov = runner(
        [
            "python",
            "-m",
            "pytest",
            "tests/unit",
            "tests/integration",
            "--cov=app.auth",
            "--cov=app.config",
            "--cov=app.services",
            "--cov-report=term-missing",
            "-q",
        ]
    )
    threshold = next(
        (c.get("threshold", 80) for c in caps["capabilities"] if c["id"] == "coverage-key-modules"),
        80,
    )
    total = _parse_coverage_total(cov.out)
    if total is not None and total < threshold:
        risky_proposals.append(
            f"Покрытие ключевых модулей {total}% ниже порога {threshold}% — добавить тесты (решение проекта)."
        )

    result.safe_applied = safe_changes
    result.proposals = risky_proposals
    if risky_proposals:
        result.proposals_path = _write_proposals(month, risky_proposals, safe_changes)


def _parse_coverage_total(out: str) -> int | None:
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("TOTAL") and line.endswith("%"):
            try:
                return int(line.split()[-1].rstrip("%"))
            except (ValueError, IndexError):
                return None
    return None


def _write_proposals(month: str, proposals: list[str], safe: list[str]) -> str:
    PROPOSALS_DIR.mkdir(parents=True, exist_ok=True)
    path = PROPOSALS_DIR / f"proposals_{month}.md"
    lines = [
        f"# Предложения самоулучшения — {month}",
        "",
        "Сгенерировано детерминированным контролёром `tools/self_improve_controller.py`.",
        "Решение принимает проект/человек через PR или issue (без автомержа рискового).",
        "",
        "## Безопасные правки (применены автоматически, обратимы)",
    ]
    lines += [f"- {s}" for s in safe] or ["- (нет)"]
    lines += ["", "## Требуют решения человека (не применялись)"]
    lines += [f"- [ ] {p}" for p in proposals] or ["- (нет)"]
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return _rel(path)


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


# --------------------------------------------------------------------------- #
# POST: журнал + heartbeat
# --------------------------------------------------------------------------- #
def write_heartbeat(result: ControllerResult, now: _dt.datetime) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"ts": now.isoformat(), "result": result.to_dict()}
    HEARTBEAT_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    with JOURNAL_FILE.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"ts": now.isoformat(), "summary": {
            "aborted": result.aborted,
            "abort_reason": result.abort_reason,
            "safe_applied": len(result.safe_applied),
            "proposals": len(result.proposals),
        }}, ensure_ascii=False) + "\n")
    result.heartbeat_path = _rel(HEARTBEAT_FILE)


# --------------------------------------------------------------------------- #
# Оркестрация
# --------------------------------------------------------------------------- #
def run_controller(
    runner: Runner | None = None,
    now: _dt.datetime | None = None,
    write_side_effects: bool = True,
) -> ControllerResult:
    runner = runner or _real_runner
    now = now or _dt.datetime.now(_dt.timezone.utc)
    month = now.strftime("%Y-%m")
    result = ControllerResult()

    # PRE
    result.baseline = run_baseline(runner)
    if baseline_is_red(result.baseline):
        result.aborted = True
        result.abort_reason = "baseline-red: критичный гейт pytest упал — правки не вносятся (safe-on-failure)."
        if write_side_effects:
            write_heartbeat(result, now)
        return result

    # SELF-DEV (с авто-revert)
    self_dev(runner, result)

    # DERIVE + HANDOFF
    derive_and_handoff(runner, result, month)

    # POST
    if write_side_effects:
        write_heartbeat(result, now)
    return result


def render_report(result: ControllerResult) -> str:
    lines = ["# Self-improve controller — отчёт", ""]
    if result.aborted:
        lines.append(f"**ABORTED**: {result.abort_reason}")
        return "\n".join(lines)
    lines.append("Baseline: " + ", ".join(f"{g.name}={'ok' if g.ok else 'FAIL'}" for g in result.baseline))
    lines.append(f"Self-dev применено: {result.self_dev_applied or '—'}")
    lines.append(f"Self-dev откачено: {result.self_dev_reverted or '—'}")
    lines.append(f"Безопасные правки проекта: {result.safe_applied or '—'}")
    lines.append(f"Предложения (решает человек): {len(result.proposals)}")
    if result.proposals_path:
        lines.append(f"Файл предложений: {result.proposals_path}")
    lines.append(f"Heartbeat: {result.heartbeat_path or '—'}")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Месячный самоулучшающийся контролёр Skaitītāji")
    parser.add_argument("--report-out", default="", help="Куда записать markdown-отчёт (для CI).")
    args = parser.parse_args(argv)

    result = run_controller()
    report = render_report(result)
    print(report)
    if args.report_out:
        Path(args.report_out).write_text(report, encoding="utf-8")
    # Всегда 0: safe-on-failure не должен ронять CI без нужды; abort — это штатный результат.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

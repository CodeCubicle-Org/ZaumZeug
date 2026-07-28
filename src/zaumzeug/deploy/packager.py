"""Deploy packager — eval gate pre-step (Architecture §6.4 / §10.2).

Single source of truth for ``deploy.eval_gate`` (E5-S06 / E6-S03). Full bundle
copy rules land in E5-S01; this module already runs the gate before packaging.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TextIO

from zaumzeug.config import (
    ConfigValidationError,
    EvalGateMode,
    HarnessConfig,
    load_harness,
)
from zaumzeug.config.harness_root import harness_dir as resolve_harness_dir
from zaumzeug.doctor.project import find_project_root
from zaumzeug.eval.runner import EvalError, EvalResult, format_eval_result, run_eval

__all__ = [
    "DEFAULT_EVAL_GATE",
    "DeployError",
    "EvalGateResult",
    "PackageResult",
    "apply_eval_gate",
    "format_eval_gate_result",
    "package_harness",
    "resolve_eval_gate",
]

DEFAULT_EVAL_GATE: EvalGateMode = "skip"

EvalRunner = Callable[..., EvalResult]
BundleWriter = Callable[..., Path]


class DeployError(RuntimeError):
    """Deploy orchestration failed with an actionable message."""

    def __init__(
        self,
        message: str,
        *,
        path: Path | None = None,
        harness_name: str | None = None,
        suggestion: str | None = None,
    ) -> None:
        self.path = Path(path) if path is not None else None
        self.harness_name = harness_name
        self.suggestion = suggestion
        super().__init__(message)


@dataclass(slots=True)
class EvalGateResult:
    """Outcome of the deploy eval gate pre-step (Architecture §6.4)."""

    mode: EvalGateMode
    skipped: bool
    blocked: bool
    eval_result: EvalResult | None = None
    messages: list[str] = field(default_factory=list)

    @property
    def eval_ran(self) -> bool:
        return self.eval_result is not None


@dataclass(slots=True)
class PackageResult:
    """Outcome of ``zaumzeug deploy`` after the eval gate (and optional pack)."""

    harness_name: str
    harness_dir: Path
    eval_gate: EvalGateResult
    packaged: bool
    bundle_dir: Path | None = None

    @property
    def exit_code(self) -> int:
        return 1 if self.eval_gate.blocked else 0


def resolve_eval_gate(
    harness_config: HarnessConfig,
    *,
    override: str | None = None,
) -> EvalGateMode:
    """Resolve gate mode: CLI ``--eval-gate`` → ``deploy.eval_gate`` → ``skip``."""
    if override is not None:
        normalized = override.strip().lower()
        if normalized not in {"skip", "warn", "block"}:
            raise DeployError(
                f"Unknown eval gate {override!r} (expected 'skip', 'warn', or 'block')",
                harness_name=harness_config.name,
                suggestion="Use --eval-gate skip|warn|block",
            )
        return normalized  # type: ignore[return-value]
    deploy = harness_config.deploy
    if deploy is not None:
        return deploy.eval_gate
    return DEFAULT_EVAL_GATE


def apply_eval_gate(
    harness_name: str,
    harness_config: HarnessConfig,
    *,
    eval_gate_override: str | None = None,
    project_root: Path | str | None = None,
    run_eval_fn: EvalRunner | None = None,
    output: TextIO | None = None,
) -> EvalGateResult:
    """Apply Architecture §6.4 gate before packaging (single source of truth).

    * ``skip`` — do not run eval.
    * ``warn`` / ``block`` — run eval when ``eval:`` is configured; if ``eval:``
      is absent, both modes are a no-op.
    * ``warn`` — print failures and continue (``blocked=False``).
    * ``block`` — abort deploy on any eval failure (``blocked=True``).
    """
    mode = resolve_eval_gate(harness_config, override=eval_gate_override)
    stream = output

    def _emit(message: str) -> None:
        if stream is not None:
            print(message, file=stream)

    if mode == "skip":
        msg = f"Eval gate: skip (deploy.eval_gate={mode})"
        _emit(msg)
        return EvalGateResult(mode=mode, skipped=True, blocked=False, messages=[msg])

    if harness_config.eval is None:
        msg = (
            f"Eval gate: {mode} — no `eval:` section; gate is a no-op "
            "(nothing to run)"
        )
        _emit(msg)
        return EvalGateResult(mode=mode, skipped=True, blocked=False, messages=[msg])

    runner = run_eval_fn or run_eval
    root = Path(project_root) if project_root is not None else None
    try:
        eval_result = runner(harness_name, project_root=root)
    except EvalError as exc:
        raise DeployError(
            f"Eval gate ({mode}) failed to run eval: {exc}",
            path=exc.path,
            harness_name=harness_name,
            suggestion=exc.suggestion or "Fix eval config or use --eval-gate skip",
        ) from exc

    summary = format_eval_result(eval_result)
    messages = [f"Eval gate: {mode}", summary]
    _emit(messages[0])
    _emit(summary)

    if eval_result.failed == 0:
        ok = f"Eval gate ({mode}): all checks passed"
        messages.append(ok)
        _emit(ok)
        return EvalGateResult(
            mode=mode,
            skipped=False,
            blocked=False,
            eval_result=eval_result,
            messages=messages,
        )

    if mode == "warn":
        warn = (
            f"Eval gate (warn): {eval_result.failed} failure(s); "
            "continuing deploy"
        )
        messages.append(warn)
        _emit(warn)
        return EvalGateResult(
            mode=mode,
            skipped=False,
            blocked=False,
            eval_result=eval_result,
            messages=messages,
        )

    block = (
        f"Eval gate (block): {eval_result.failed} failure(s); "
        "aborting deploy"
    )
    messages.append(block)
    _emit(block)
    return EvalGateResult(
        mode=mode,
        skipped=False,
        blocked=True,
        eval_result=eval_result,
        messages=messages,
    )


def format_eval_gate_result(result: EvalGateResult) -> str:
    """Human-readable gate summary for CLI / tests."""
    return "\n".join(result.messages)


def _default_write_bundle(
    harness_name: str,
    *,
    project_root: Path,
    harness_dir: Path,
    harness_config: HarnessConfig,
) -> Path:
    """Placeholder pack step until E5-S01 lands full copy rules.

    Creates ``deploy/<name>/`` so gate integration can assert packaging continued.
    Full stripped yaml / artifacts / manifest are E5-S01.
    """
    del harness_dir, harness_config  # reserved for E5-S01 copy rules
    dest = project_root / "deploy" / harness_name
    dest.mkdir(parents=True, exist_ok=True)
    marker = dest / ".zaumzeug-deploy-gate-ok"
    marker.write_text(
        "Eval gate passed. Full deploy packaging lands in E5-S01.\n",
        encoding="utf-8",
    )
    return dest


def package_harness(
    harness_name: str,
    *,
    eval_gate: str | None = None,
    project_root: Path | str | None = None,
    run_eval_fn: EvalRunner | None = None,
    write_bundle: BundleWriter | None = None,
    output: TextIO | None = None,
) -> PackageResult:
    """Run deploy packager: eval gate (§6.4) then bundle write (E5-S01 body).

    *eval_gate* is the CLI ``--eval-gate`` override. Inject *run_eval_fn* /
    *write_bundle* in unit tests.
    """
    root = Path(project_root) if project_root is not None else find_project_root()
    harness_path = resolve_harness_dir(root, harness_name, deploy=False)
    harness_yaml = harness_path / "harness.yaml"
    if not harness_yaml.is_file():
        raise DeployError(
            f"Harness '{harness_name}' not found at {harness_path} (missing harness.yaml)",
            path=harness_path,
            harness_name=harness_name,
            suggestion=f"Create the harness with `zaumzeug init {harness_name}`",
        )

    try:
        harness_config = load_harness(harness_yaml)
    except ConfigValidationError as exc:
        raise DeployError(
            str(exc),
            path=exc.path,
            harness_name=harness_name,
            suggestion=f"Fix harness.yaml at {harness_yaml}",
        ) from exc

    gate = apply_eval_gate(
        harness_name,
        harness_config,
        eval_gate_override=eval_gate,
        project_root=root,
        run_eval_fn=run_eval_fn,
        output=output,
    )
    if gate.blocked:
        return PackageResult(
            harness_name=harness_name,
            harness_dir=harness_path,
            eval_gate=gate,
            packaged=False,
            bundle_dir=None,
        )

    writer = write_bundle or _default_write_bundle
    bundle_dir = writer(
        harness_name,
        project_root=root,
        harness_dir=harness_path,
        harness_config=harness_config,
    )
    return PackageResult(
        harness_name=harness_name,
        harness_dir=harness_path,
        eval_gate=gate,
        packaged=True,
        bundle_dir=Path(bundle_dir),
    )

# Story: E6-S04 / E6.4
"""E6-S04 — ``eval/`` pytest scaffold (DeepEval + custom metrics)."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

from zaumzeug.doctor.project import find_project_root
from zaumzeug.scaffold import init_harness

_REPO_ROOT = find_project_root()
_EXAMPLE_EVAL = _REPO_ROOT / "usr-harnesses" / "example" / "eval"

deepeval = pytest.importorskip(
    "deepeval",
    reason='requires pip install "zaumzeug[eval]"',
)


def test_e6_s04_ac1_deepeval_test_run() -> None:
    """AC-1: Optional ``usr-harnesses/<name>/eval/test_*.py`` runs via ``deepeval test run``."""
    assert _EXAMPLE_EVAL.is_dir(), f"missing example eval scaffold: {_EXAMPLE_EVAL}"
    tests = sorted(_EXAMPLE_EVAL.glob("test_*.py"))
    assert tests, f"expected test_*.py under {_EXAMPLE_EVAL}"

    deepeval_bin = Path(sys.executable).resolve().parent / (
        "deepeval.exe" if os.name == "nt" else "deepeval"
    )
    if not deepeval_bin.is_file():
        pytest.fail(f"deepeval CLI not found next to interpreter: {deepeval_bin}")

    env = os.environ.copy()
    env.setdefault("DEEPEVAL_TELEMETRY_OPT_OUT", "YES")
    # Windows consoles default to cp1252; DeepEval progress uses emoji.
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    # Keep Confident AI / cloud sync off for local scaffold smoke.
    env.setdefault("DEEPEVAL_RESULTS_FOLDER", str(_EXAMPLE_EVAL / ".results"))

    proc = subprocess.run(
        [str(deepeval_bin), "test", "run", str(_EXAMPLE_EVAL)],
        cwd=str(_REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    assert proc.returncode == 0, (
        f"deepeval test run failed (exit {proc.returncode})\n"
        f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )


def test_e6_s04_ac2_custom_metrics_importable(tmp_path: Path) -> None:
    """AC-2: Custom metrics in ``eval/metrics.py`` are importable."""
    metrics_path = _EXAMPLE_EVAL / "metrics.py"
    assert metrics_path.is_file()

    spec = importlib.util.spec_from_file_location(
        "example_eval_metrics",
        metrics_path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    metric_cls = getattr(module, "ContainsSubstringMetric", None)
    assert metric_cls is not None
    metric = metric_cls("ZaumZeug")
    from deepeval.test_case import LLMTestCase

    case = LLMTestCase(
        input="ping",
        actual_output="ZaumZeug harness reply",
    )
    score = metric.measure(case)
    assert score == 1.0
    assert metric.is_successful() is True

    # Init --with-eval also ships importable metrics.py
    project_root = tmp_path / "project"
    (project_root / "usr-harnesses").mkdir(parents=True)
    harness_dir = init_harness("scoped", project_root=project_root, with_eval=True)
    init_metrics = harness_dir / "eval" / "metrics.py"
    assert init_metrics.is_file()
    text = init_metrics.read_text(encoding="utf-8")
    assert "ContainsSubstringMetric" in text
    assert "scoped" in (harness_dir / "eval" / "test_smoke.py").read_text(
        encoding="utf-8"
    )

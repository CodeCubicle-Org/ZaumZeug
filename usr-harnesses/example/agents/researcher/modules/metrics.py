"""Optional GEPA metric with DeepEval ``.measure()`` delegation (E6-S07).

``zaumzeug compile`` loads ``metric`` from this module when present. DeepEval
is **optional** — without ``pip install "zaumzeug[eval]"``, the bridge falls
back to the default keyword GEPA metric (score + textual feedback).

Enable DeepEval scoring by keeping ``USE_DEEPEVAL = True`` (default) after
installing the ``[eval]`` extra. Set ``USE_DEEPEVAL = False`` to force the
builtin keyword metric even when DeepEval is installed.
"""

from __future__ import annotations

from typing import Any

from zaumzeug.eval.gepa_bridge import deepeval_gepa_metric

# Flip to False to skip DeepEval even when the [eval] extra is installed.
USE_DEEPEVAL = True


def _expected_in_output_metric_factory() -> Any:
    """Lazy DeepEval metric: pass when expected answer appears in the prediction."""
    from deepeval.metrics import BaseMetric
    from deepeval.test_case import LLMTestCase

    class ExpectedInOutputMetric(BaseMetric):
        def __init__(self, *, threshold: float = 1.0) -> None:
            self.threshold = threshold
            self.score: float | None = None
            self.success: bool | None = None
            self.reason: str | None = None
            self.error: str | None = None

        def measure(self, test_case: LLMTestCase) -> float:
            try:
                expected = (test_case.expected_output or "").strip()
                actual = test_case.actual_output or ""
                if not expected:
                    self.score = 1.0 if actual.strip() else 0.0
                    self.reason = (
                        "Good." if self.score >= 1.0 else "Provide a non-empty answer."
                    )
                else:
                    found = expected in actual
                    self.score = 1.0 if found else 0.0
                    self.reason = (
                        "Good."
                        if found
                        else f"Include expected keyword in answer: {expected!r}."
                    )
                self.success = self.score >= self.threshold
                return self.score
            except Exception as exc:  # noqa: BLE001 — DeepEval metric contract
                self.error = str(exc)
                raise

        async def a_measure(self, test_case: LLMTestCase) -> float:
            return self.measure(test_case)

        def is_successful(self) -> bool:
            if self.error is not None:
                self.success = False
            return bool(self.success)

        @property
        def __name__(self) -> str:
            return "Expected In Output"

    return ExpectedInOutputMetric()


# GEPA entry point — compile loads this as the metric callable.
metric = deepeval_gepa_metric(
    _expected_in_output_metric_factory if USE_DEEPEVAL else None,
    enabled=USE_DEEPEVAL,
)

"""Custom DeepEval metrics for the example harness (dev-only; not shipped in deploy).

Requires: ``pip install "zaumzeug[eval]"``.
Run tests: ``deepeval test run usr-harnesses/example/eval/``
"""

from __future__ import annotations

from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase


class ContainsSubstringMetric(BaseMetric):
    """Pass when ``actual_output`` contains a required substring (no LLM judge)."""

    def __init__(
        self,
        substring: str,
        *,
        threshold: float = 1.0,
        case_sensitive: bool = False,
    ) -> None:
        self.substring = substring
        self.threshold = threshold
        self.case_sensitive = case_sensitive
        self.score: float | None = None
        self.success: bool | None = None
        self.reason: str | None = None
        self.error: str | None = None

    def measure(self, test_case: LLMTestCase) -> float:
        try:
            actual = test_case.actual_output or ""
            needle = self.substring
            haystack = actual if self.case_sensitive else actual.lower()
            target = needle if self.case_sensitive else needle.lower()
            found = target in haystack
            self.score = 1.0 if found else 0.0
            self.success = self.score >= self.threshold
            self.reason = (
                f"Found {needle!r} in actual_output"
                if found
                else f"Missing {needle!r} in actual_output"
            )
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
        return "Contains Substring"

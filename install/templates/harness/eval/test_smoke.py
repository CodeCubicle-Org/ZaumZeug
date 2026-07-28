"""Optional DeepEval smoke test for harness ``{{name}}``.

Requires: ``pip install "zaumzeug[eval]"``.
Run: ``deepeval test run usr-harnesses/{{name}}/eval/``

Replace ``actual_output`` with agent output from ``zaumzeug run`` or a captured
trace once you have real cases (Architecture §13.6).
"""

from __future__ import annotations

from deepeval import assert_test
from deepeval.test_case import LLMTestCase

from metrics import ContainsSubstringMetric


def test_smoke_output_mentions_harness() -> None:
    """Deterministic custom metric — no LLM judge / API key required."""
    metric = ContainsSubstringMetric("{{name}}", threshold=1.0)
    case = LLMTestCase(
        input="What harness is this?",
        actual_output="This is the {{name}} harness scaffold.",
    )
    assert_test(case, [metric])

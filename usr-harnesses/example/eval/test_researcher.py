"""Optional DeepEval pytest cases for the example harness (E6-S04).

Requires: ``pip install "zaumzeug[eval]"``.
Run: ``deepeval test run usr-harnesses/example/eval/``

``actual_output`` below is a fixture string for scaffold smoke. Replace with
agent output from ``zaumzeug run example`` or a captured trace for real
regression cases (see user-docs/guides/testing.md).
"""

from __future__ import annotations

from deepeval import assert_test
from deepeval.test_case import LLMTestCase

from metrics import ContainsSubstringMetric


def test_researcher_mentions_zaumzeug() -> None:
    """Deterministic custom metric — no LLM judge / API key required."""
    metric = ContainsSubstringMetric("ZaumZeug", threshold=1.0)
    case = LLMTestCase(
        input="Summarize ZaumZeug workflow.yaml",
        actual_output=(
            "ZaumZeug uses workflow.yaml to run serial agent stages "
            "for the example research harness."
        ),
    )
    assert_test(case, [metric])

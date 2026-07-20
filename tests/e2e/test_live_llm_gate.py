# Story: E3-S06
"""Live e2e tests — gated by ``HARNESS_LIVE_LLM=1`` (Architecture §13.1).

Default CI must never set this env var. Placeholder until live smoke cases land.
"""

from __future__ import annotations

import os

import pytest

pytestmark = [
    pytest.mark.live_llm,
    pytest.mark.skipif(
        os.environ.get("HARNESS_LIVE_LLM") != "1",
        reason="set HARNESS_LIVE_LLM=1 to run live provider e2e",
    ),
]


def test_e3_s06_live_llm_gate_placeholder() -> None:
    """Placeholder: real live-provider smoke tests land with later stories."""
    assert os.environ.get("HARNESS_LIVE_LLM") == "1"

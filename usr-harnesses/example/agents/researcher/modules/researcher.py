"""Example research DSPy module for ``zaumzeug compile`` (Phase 2 / E4).

Optimized offline by GEPA; ``compile/export.py`` maps ``dump_state()`` into
Haystack ``prompts/system.md`` + ``artifact-manifest.json`` (E4-S03a).
"""

from __future__ import annotations

import dspy


class ResearchModule(dspy.Module):
    """Minimal Pattern A module mirroring the example researcher role."""

    def __init__(self) -> None:
        super().__init__()
        self.respond = dspy.Predict("question -> answer")

    def forward(self, question: str) -> dspy.Prediction:
        return self.respond(question=question)

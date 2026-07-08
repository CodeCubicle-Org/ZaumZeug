"""Mock ChatGenerator for CI and local dev without live API keys (E3-S05)."""

from __future__ import annotations

import json
from importlib import resources
from pathlib import Path
from typing import Any

from haystack import component
from haystack.dataclasses import ChatMessage

_PACKAGE_FIXTURES = "zaumzeug.fixtures.responses"
_REPO_FIXTURES = Path("tests") / "fixtures" / "responses"


def resolve_fixture_dir(
    *,
    fixture_dir: Path | str | None = None,
    project_root: Path | str | None = None,
) -> Path:
    """Return the directory that holds canned mock LLM fixture files."""
    if fixture_dir is not None:
        return Path(fixture_dir)

    if project_root is not None:
        repo_dir = Path(project_root) / _REPO_FIXTURES
        if repo_dir.is_dir():
            return repo_dir

    cwd = Path.cwd()
    for parent in (cwd, *cwd.parents):
        candidate = parent / _REPO_FIXTURES
        if candidate.is_dir():
            return candidate

    return Path(resources.files(_PACKAGE_FIXTURES))  # type: ignore[arg-type]


def load_fixture_response(
    model: str,
    *,
    fixture_dir: Path | str | None = None,
    project_root: Path | str | None = None,
) -> str:
    """Load canned assistant text for *model* from fixture files."""
    base = resolve_fixture_dir(fixture_dir=fixture_dir, project_root=project_root)
    json_path = base / f"{model}.json"
    if json_path.is_file():
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        if isinstance(payload, dict) and "content" in payload:
            return str(payload["content"])
        raise ValueError(
            f"fixture {json_path} must be a JSON object with a 'content' string"
        )

    text_path = base / f"{model}.txt"
    if text_path.is_file():
        return text_path.read_text(encoding="utf-8").strip()

    raise FileNotFoundError(
        f"no mock fixture for model {model!r} under {base} "
        f"(expected {model}.txt or {model}.json)"
    )


@component
class MockChatGenerator:
    """Haystack ChatGenerator that returns deterministic fixture text."""

    def __init__(
        self,
        model: str,
        *,
        fixture_dir: Path | str | None = None,
        project_root: Path | str | None = None,
        generation_kwargs: dict[str, Any] | None = None,
    ) -> None:
        self.model = model
        self._fixture_dir = fixture_dir
        self._project_root = project_root
        self.generation_kwargs = generation_kwargs or {}

    def run(
        self,
        messages: list[ChatMessage] | str,
        generation_kwargs: dict[str, Any] | None = None,
        tools: Any = None,
        **kwargs: Any,
    ) -> dict[str, list[ChatMessage]]:
        del messages, generation_kwargs, tools, kwargs
        content = load_fixture_response(
            self.model,
            fixture_dir=self._fixture_dir,
            project_root=self._project_root,
        )
        return {"replies": [ChatMessage.from_assistant(content)]}

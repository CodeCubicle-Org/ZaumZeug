"""Config-driven ModelRouter — dispatches to Haystack ChatGenerators (Architecture §7)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from haystack.dataclasses import ChatMessage

from zaumzeug.config.models import AgentModelsConfig, ModelEntryConfig
from zaumzeug.integrations.mock import MockChatGenerator

# Provider id → (module, class name). Mock is built-in; live providers added in E3-S01.
PROVIDERS: dict[str, tuple[str, str]] = {
    "mock": ("zaumzeug.integrations.mock", "MockChatGenerator"),
}


class ModelRouterError(RuntimeError):
    """Raised when ModelRouter cannot resolve or build a generator."""


class ModelRouter:
    """Stage-scoped router over a merged per-agent model registry."""

    def __init__(
        self,
        models_config: AgentModelsConfig,
        *,
        fixture_dir: Path | str | None = None,
        project_root: Path | str | None = None,
    ) -> None:
        self._models_config = models_config
        self._fixture_dir = fixture_dir
        self._project_root = Path(project_root) if project_root is not None else None
        self._generator_cache: dict[str, Any] = {}

    @property
    def models_config(self) -> AgentModelsConfig:
        return self._models_config

    def resolve_model_id(self, model_id: str | None = None) -> str:
        """Return explicit *model_id* or the registry default."""
        if model_id is not None and model_id.strip():
            return model_id.strip()
        return self._models_config.default_model_id

    def get_entry(self, model_id: str | None = None) -> ModelEntryConfig:
        """Look up a registry entry for *model_id* (or default)."""
        resolved = self.resolve_model_id(model_id)
        try:
            return self._models_config.models[resolved]
        except KeyError as exc:
            raise ModelRouterError(
                f"model_id {resolved!r} is not defined in the merged model registry"
            ) from exc

    def build_generator(self, model_id: str | None = None) -> Any:
        """Lazily construct and cache a ChatGenerator for the resolved entry."""
        entry = self.get_entry(model_id)
        if entry.provider in self._generator_cache:
            return self._generator_cache[entry.provider]

        generator = self._build_generator(entry)
        self._generator_cache[entry.provider] = generator
        return generator

    def run(
        self,
        messages: list[ChatMessage] | str,
        *,
        model_id: str | None = None,
        **kwargs: Any,
    ) -> dict[str, list[ChatMessage]]:
        """Run the resolved ChatGenerator for *model_id*."""
        generator = self.build_generator(model_id)
        return generator.run(messages, **kwargs)

    def _build_generator(self, entry: ModelEntryConfig) -> Any:
        if entry.provider == "mock":
            return MockChatGenerator(
                model=entry.model,
                fixture_dir=self._fixture_dir,
                project_root=self._project_root,
                generation_kwargs=entry.generation_kwargs,
            )

        if entry.provider not in PROVIDERS:
            raise ModelRouterError(
                f"provider {entry.provider!r} is not available in Phase 1 "
                f"(supported: {', '.join(sorted(PROVIDERS))})"
            )

        module_path, class_name = PROVIDERS[entry.provider]
        try:
            import importlib

            module = importlib.import_module(module_path)
            generator_cls = getattr(module, class_name)
        except ImportError as exc:
            raise ModelRouterError(
                f"provider package for {entry.provider!r} is not installed "
                f"(import {module_path} failed: {exc})"
            ) from exc

        return generator_cls(
            model=entry.model,
            generation_kwargs=entry.generation_kwargs or {},
        )

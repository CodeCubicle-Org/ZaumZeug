"""Haystack ChatGenerator provider map and factory (E3-S01)."""

from __future__ import annotations

import importlib
import os
from typing import Any

from haystack.utils import Secret

from zaumzeug.config.models import ModelEntryConfig
from zaumzeug.config.schemas import CURRENT_SDK_PHASE
from zaumzeug.integrations.mock import MockChatGenerator

# Phase 1 allowlist (Architecture §7).
PHASE_1_PROVIDERS: frozenset[str] = frozenset(
    {"mock", "openrouter", "openai_compatible"}
)

# Native cloud providers deferred to Phase 2+.
PHASE_2_NATIVE_PROVIDERS: frozenset[str] = frozenset(
    {
        "openai",
        "anthropic",
        "azure",
        "cohere",
        "gemini",
        "google",
        "mistral",
        "groq",
    }
)

# Provider id → (import module, class name).
PROVIDERS: dict[str, tuple[str, str]] = {
    "mock": ("zaumzeug.integrations.mock", "MockChatGenerator"),
    "openrouter": (
        "haystack_integrations.components.generators.openrouter",
        "OpenRouterChatGenerator",
    ),
    "openai_compatible": (
        "haystack.components.generators.chat",
        "OpenAIChatGenerator",
    ),
    "openai": ("haystack.components.generators.chat", "OpenAIChatGenerator"),
    "anthropic": (
        "haystack_integrations.components.generators.anthropic",
        "AnthropicChatGenerator",
    ),
}

# pip install hints when an integration package is missing.
PROVIDER_INSTALL_HINTS: dict[str, str] = {
    "openrouter": "pip install openrouter-haystack",
    "openai_compatible": "pip install openai-haystack",
    "openai": "pip install openai-haystack",
    "anthropic": "pip install anthropic-haystack",
}

_DEFAULT_OPENAI_API_BASE_ENV = "OPENAI_API_BASE"
_DEFAULT_OPENAI_API_KEY_ENV = "OPENAI_API_KEY"


class ProviderBuildError(RuntimeError):
    """Raised when a Haystack ChatGenerator cannot be constructed."""


def provider_cache_key(entry: ModelEntryConfig) -> tuple[str, str, str]:
    """Cache key: provider + resolved endpoint + model name."""
    return (entry.provider, resolve_api_base_url(entry) or "", entry.model)


def resolve_api_base_url(entry: ModelEntryConfig) -> str | None:
    """Return the OpenAI-compatible base URL for *entry*, if applicable."""
    if entry.api_base_url:
        return entry.api_base_url.strip()
    if entry.provider == "openai_compatible":
        env_value = os.environ.get(_DEFAULT_OPENAI_API_BASE_ENV, "").strip()
        return env_value or None
    return None


def is_phase_gated_provider(provider: str) -> bool:
    """Return True when *provider* is not available in the current SDK phase."""
    if provider in PHASE_1_PROVIDERS:
        return False
    if provider in PHASE_2_NATIVE_PROVIDERS:
        return CURRENT_SDK_PHASE < 2
    return provider not in PROVIDERS


def phase_hint_for_provider(provider: str) -> str:
    """Human-readable phase guidance for unsupported providers."""
    if provider in PHASE_2_NATIVE_PROVIDERS:
        return (
            f"provider {provider!r} is not available until Phase 2 "
            f"(use 'openrouter' or 'openai_compatible' in Phase 1)"
        )
    supported = ", ".join(sorted(PHASE_1_PROVIDERS))
    return (
        f"provider {provider!r} is not available in Phase {CURRENT_SDK_PHASE} "
        f"(supported: {supported})"
    )


def import_generator_class(provider: str) -> type[Any]:
    """Import the Haystack ChatGenerator class for *provider*."""
    if provider not in PROVIDERS:
        raise ProviderBuildError(phase_hint_for_provider(provider))

    module_path, class_name = PROVIDERS[provider]
    try:
        module = importlib.import_module(module_path)
        return getattr(module, class_name)
    except ImportError as exc:
        hint = PROVIDER_INSTALL_HINTS.get(provider, f"pip install {provider}-haystack")
        raise ProviderBuildError(
            f"provider package for {provider!r} is not installed "
            f"({hint}; import {module_path} failed: {exc})"
        ) from exc


def build_chat_generator(
    entry: ModelEntryConfig,
    *,
    fixture_dir: Any = None,
    project_root: Any = None,
) -> Any:
    """Construct a Haystack ChatGenerator for a registry *entry*."""
    if is_phase_gated_provider(entry.provider):
        raise ProviderBuildError(phase_hint_for_provider(entry.provider))

    if entry.provider == "mock":
        return MockChatGenerator(
            model=entry.model,
            fixture_dir=fixture_dir,
            project_root=project_root,
            generation_kwargs=entry.generation_kwargs,
        )

    generator_cls = import_generator_class(entry.provider)
    kwargs: dict[str, Any] = {
        "model": entry.model,
        "generation_kwargs": entry.generation_kwargs or {},
    }

    if entry.provider == "openrouter":
        kwargs["api_key"] = Secret.from_env_var("OPENROUTER_API_KEY")
        return generator_cls(**kwargs)

    if entry.provider == "openai_compatible":
        api_base_url = resolve_api_base_url(entry)
        if not api_base_url:
            raise ProviderBuildError(
                "openai_compatible provider requires api_base_url in agents-models.yaml "
                f"or {_DEFAULT_OPENAI_API_BASE_ENV} in .env "
                "(e.g. http://localhost:1234/v1 for LM Studio)"
            )
        kwargs["api_base_url"] = api_base_url
        api_key = os.environ.get(_DEFAULT_OPENAI_API_KEY_ENV, "").strip()
        if api_key:
            kwargs["api_key"] = Secret.from_token(api_key)
        else:
            kwargs["api_key"] = Secret.from_token("not-needed")
        return generator_cls(**kwargs)

    if entry.provider == "openai":
        kwargs["api_key"] = Secret.from_env_var("OPENAI_API_KEY")
        api_base_url = resolve_api_base_url(entry)
        if api_base_url:
            kwargs["api_base_url"] = api_base_url
        return generator_cls(**kwargs)

    return generator_cls(**kwargs)

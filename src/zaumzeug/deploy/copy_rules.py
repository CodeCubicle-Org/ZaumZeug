"""Dev-vs-deploy path policy, strip helpers, and copy-matrix resolver (§10.1).

Exclude sets are shared with E6-S04. Strip helpers support the packager.
``resolve_deploy_copy_plan`` encodes Architecture §10.1 include rules so
dev-only paths never enter production bundles (E5-S02).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Literal

from zaumzeug.runtime.tools.custom import CustomToolError, custom_tool_source_rel

__all__ = [
    "ALWAYS_INCLUDED_HARNESS_FILES",
    "CopyEntry",
    "CopyKind",
    "CopyRulesError",
    "DEV_ONLY_AGENT_DIRS",
    "DEV_ONLY_TOP_LEVEL_DIRS",
    "DeployCopyPlan",
    "STRIPPED_AGENT_KEYS",
    "STRIPPED_HARNESS_KEYS",
    "assert_required_paths",
    "is_excluded_from_deploy",
    "resolve_deploy_copy_plan",
    "strip_agent_yaml",
    "strip_harness_yaml",
]

# Top-level under usr-harnesses/<name>/ — never copied to deploy/<name>/.
DEV_ONLY_TOP_LEVEL_DIRS: frozenset[str] = frozenset({"data", "eval"})

# Under agents/<agent-name>/ — never copied to deploy.
DEV_ONLY_AGENT_DIRS: frozenset[str] = frozenset({"modules", "skills", "data"})

# Dropped from harness.yaml in the deploy bundle (Architecture §10.2 step 3).
STRIPPED_HARNESS_KEYS: frozenset[str] = frozenset({"compile", "eval", "deploy"})

# Dropped from agent.yaml in the deploy bundle (E5-S02 AC-5).
STRIPPED_AGENT_KEYS: frozenset[str] = frozenset({"compile"})

# Always expected at harness root / docs (Architecture §10.1 / AC-4).
ALWAYS_INCLUDED_HARNESS_FILES: tuple[str, ...] = (
    "harness.yaml",
    "workflow.yaml",
    "docs/workflow-diagram.md",
)

CopyKind = Literal[
    "harness_yaml",
    "workflow",
    "diagram",
    "agents_models",
    "agent_yaml",
    "prompt",
    "tool",
    "hooks",
    "artifact_pin",
    "pipeline",
]


class CopyRulesError(ValueError):
    """Copy-matrix resolution or required-path validation failed."""

    def __init__(
        self,
        message: str,
        *,
        path: Path | None = None,
        missing: Sequence[str] | None = None,
        suggestion: str | None = None,
    ) -> None:
        self.path = Path(path) if path is not None else None
        self.missing = tuple(missing) if missing is not None else ()
        self.suggestion = suggestion
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class CopyEntry:
    """One Architecture §10.1 include row (harness-relative source path)."""

    relative_path: str
    kind: CopyKind
    required: bool = True
    agent_name: str | None = None


@dataclass(frozen=True, slots=True)
class DeployCopyPlan:
    """Resolved include matrix for one harness deploy."""

    entries: tuple[CopyEntry, ...]

    def paths(self) -> tuple[str, ...]:
        return tuple(entry.relative_path for entry in self.entries)

    def of_kind(self, kind: CopyKind) -> tuple[CopyEntry, ...]:
        return tuple(entry for entry in self.entries if entry.kind == kind)

    def for_agent(self, agent_name: str) -> tuple[CopyEntry, ...]:
        return tuple(entry for entry in self.entries if entry.agent_name == agent_name)


def is_excluded_from_deploy(relative_path: str | Path) -> bool:
    """Return True if *relative_path* (harness-relative) must not enter the bundle.

    Paths may use ``/`` or ``\\``; both are normalized before segment checks
    (Architecture §10.1). Comparison is case-sensitive on path segment names.
    """
    # Normalize Windows separators so Linux CI accepts harness-relative strings
    # written with backslashes (Path.as_posix() alone does not rewrite ``\\``).
    normalized = str(relative_path).replace("\\", "/")
    parts = PurePosixPath(normalized).parts
    if not parts:
        return False
    if parts[0] in DEV_ONLY_TOP_LEVEL_DIRS:
        return True
    if len(parts) >= 3 and parts[0] == "agents" and parts[2] in DEV_ONLY_AGENT_DIRS:
        return True
    return False


def strip_harness_yaml(data: dict[str, Any]) -> dict[str, Any]:
    """Return a harness.yaml mapping without ``compile`` / ``eval`` / ``deploy``."""
    return {key: value for key, value in data.items() if key not in STRIPPED_HARNESS_KEYS}


def strip_agent_yaml(data: dict[str, Any]) -> dict[str, Any]:
    """Return an agent.yaml mapping without the ``compile`` section."""
    return {key: value for key, value in data.items() if key not in STRIPPED_AGENT_KEYS}


def _posix(rel: str) -> str:
    return str(rel).replace("\\", "/").lstrip("./")


def _system_prompt_refs(agent_data: Mapping[str, Any]) -> list[str]:
    refs: list[str] = []
    top = agent_data.get("system_prompt")
    if isinstance(top, str) and top.strip():
        refs.append(top.strip())
    nested = agent_data.get("agent")
    if isinstance(nested, Mapping):
        nested_prompt = nested.get("system_prompt")
        if isinstance(nested_prompt, str) and nested_prompt.strip():
            refs.append(nested_prompt.strip())
    # Preserve order, drop duplicates.
    return list(dict.fromkeys(refs))


def _artifact_ref(agent_data: Mapping[str, Any]) -> str | None:
    top = agent_data.get("artifact")
    if isinstance(top, str) and top.strip():
        return top.strip()
    nested = agent_data.get("agent")
    if isinstance(nested, Mapping):
        value = nested.get("artifact")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _custom_tool_refs(agent_data: Mapping[str, Any]) -> list[str]:
    tools = agent_data.get("tools")
    if not isinstance(tools, Mapping):
        return []
    custom = tools.get("custom")
    if not isinstance(custom, list):
        return []
    refs: list[str] = []
    for entry in custom:
        if isinstance(entry, str) and entry.strip():
            try:
                refs.append(custom_tool_source_rel(entry.strip()))
            except CustomToolError:
                refs.append(_posix(entry.strip()))
    return list(dict.fromkeys(refs))


def _hooks_enabled(agent_data: Mapping[str, Any]) -> bool:
    hooks = agent_data.get("hooks")
    return isinstance(hooks, Mapping) and hooks.get("enabled") is True


def _exposed_pipeline_ids(harness_raw: Mapping[str, Any]) -> list[str]:
    serve = harness_raw.get("serve")
    if not isinstance(serve, Mapping):
        return []
    expose = serve.get("expose")
    if not isinstance(expose, list):
        return []
    ids: list[str] = []
    for item in expose:
        if isinstance(item, str) and item.strip():
            ids.append(item.strip())
            continue
        if isinstance(item, Mapping):
            path = item.get("path")
            pipeline_id = item.get("id")
            if isinstance(path, str) and path.strip():
                ids.append(path.strip())
            elif isinstance(pipeline_id, str) and pipeline_id.strip():
                ids.append(pipeline_id.strip())
    return list(dict.fromkeys(ids))


def resolve_deploy_copy_plan(
    *,
    harness_raw: Mapping[str, Any],
    agents: Mapping[str, Mapping[str, Any]],
) -> DeployCopyPlan:
    """Resolve Architecture §10.1 include matrix from harness + agent YAML dicts.

    Does not inspect the filesystem. Call :func:`assert_required_paths` before
    packaging. Artifact entries keep the agent.yaml ref as written (e.g.
    ``agents/foo/artifacts/RUN`` or ``…/current``); the packager may rewrite
    ``current`` to an immutable run id when copying.
    """
    entries: list[CopyEntry] = [
        CopyEntry("harness.yaml", "harness_yaml"),
        CopyEntry("workflow.yaml", "workflow"),
        CopyEntry("docs/workflow-diagram.md", "diagram"),
    ]

    for pipeline_id in _exposed_pipeline_ids(harness_raw):
        # Prefer explicit .yaml/.yml in the id; otherwise record stem for
        # filesystem resolution in assert_required_paths / packager.
        rel = _posix(pipeline_id)
        if not rel.startswith("pipelines/"):
            if rel.endswith((".yaml", ".yml")):
                rel = f"pipelines/{rel}"
            else:
                rel = f"pipelines/{rel}.yaml"
        entries.append(CopyEntry(rel, "pipeline", required=True))

    for agent_name, agent_data in agents.items():
        prefix = f"agents/{agent_name}"
        entries.append(
            CopyEntry(f"{prefix}/agent.yaml", "agent_yaml", agent_name=agent_name)
        )
        entries.append(
            CopyEntry(
                f"{prefix}/agents-models.yaml",
                "agents_models",
                agent_name=agent_name,
            )
        )

        artifact = _artifact_ref(agent_data)
        if artifact is not None:
            art_rel = _posix(artifact)
            if not art_rel.startswith("agents/"):
                art_rel = f"{prefix}/{art_rel}"
            entries.append(
                CopyEntry(
                    art_rel,
                    "artifact_pin",
                    required=True,
                    agent_name=agent_name,
                )
            )
        else:
            for prompt_ref in _system_prompt_refs(agent_data):
                prompt_rel = _posix(prompt_ref)
                if Path(prompt_rel).is_absolute() or prompt_rel.startswith("agents/"):
                    # Absolute / already-qualified — keep basename under prompts/
                    # for plan display; packager copies by resolved path.
                    if not prompt_rel.startswith("agents/"):
                        prompt_rel = f"{prefix}/prompts/{Path(prompt_rel).name}"
                else:
                    prompt_rel = f"{prefix}/{prompt_rel}"
                entries.append(
                    CopyEntry(
                        prompt_rel,
                        "prompt",
                        required=True,
                        agent_name=agent_name,
                    )
                )

        for tool_ref in _custom_tool_refs(agent_data):
            tool_rel = tool_ref if tool_ref.startswith("agents/") else f"{prefix}/{tool_ref}"
            entries.append(
                CopyEntry(tool_rel, "tool", required=True, agent_name=agent_name)
            )

        if _hooks_enabled(agent_data):
            entries.append(
                CopyEntry(
                    f"{prefix}/hooks.py",
                    "hooks",
                    required=True,
                    agent_name=agent_name,
                )
            )

    # Never emit excluded paths (defence in depth if callers pass bad refs).
    filtered = tuple(
        entry
        for entry in entries
        if not is_excluded_from_deploy(entry.relative_path)
    )
    return DeployCopyPlan(entries=filtered)


def _pipeline_candidates(harness_dir: Path, relative_path: str) -> list[Path]:
    """Resolve pipeline id to possible files under pipelines/."""
    rel = _posix(relative_path)
    direct = harness_dir / rel
    candidates = [direct]
    stem = PurePosixPath(rel).name
    if stem.endswith((".yaml", ".yml")):
        base = stem.rsplit(".", 1)[0]
    else:
        base = stem
    pipelines = harness_dir / "pipelines"
    candidates.extend(
        [
            pipelines / f"{base}.yaml",
            pipelines / f"{base}.yml",
            pipelines / base,
        ]
    )
    # Deduplicate while preserving order.
    seen: set[Path] = set()
    unique: list[Path] = []
    for path in candidates:
        resolved = path
        if resolved in seen:
            continue
        seen.add(resolved)
        unique.append(resolved)
    return unique


def assert_required_paths(harness_dir: Path | str, plan: DeployCopyPlan) -> None:
    """Fail when a required runtime path from the copy plan is missing on disk.

    Raises :class:`CopyRulesError` with the missing harness-relative paths.
    """
    root = Path(harness_dir)
    missing: list[str] = []
    first_path: Path | None = None

    for entry in plan.entries:
        if not entry.required:
            continue
        if entry.kind == "artifact_pin":
            path = root / entry.relative_path
            if not path.is_dir():
                missing.append(entry.relative_path)
                first_path = first_path or path
            continue
        if entry.kind == "pipeline":
            found = next(
                (p for p in _pipeline_candidates(root, entry.relative_path) if p.is_file()),
                None,
            )
            if found is None:
                missing.append(entry.relative_path)
                first_path = first_path or (root / entry.relative_path)
            continue

        path = root / entry.relative_path
        if not path.is_file():
            missing.append(entry.relative_path)
            first_path = first_path or path

    if not missing:
        return

    listed = ", ".join(missing)
    raise CopyRulesError(
        f"Deploy copy matrix requires missing path(s): {listed}",
        path=first_path,
        missing=missing,
        suggestion=(
            "Add the referenced runtime file(s) or remove the reference from "
            "harness.yaml / agent.yaml before deploying"
        ),
    )

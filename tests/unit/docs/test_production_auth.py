# Story: E8-S02 / E8.2
"""E8-S02 — Production auth (docs content assertions)."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
LIVE_GUIDE = REPO_ROOT / "user-docs" / "guides" / "production-auth.md"
TEMPLATE_GUIDE = (
    REPO_ROOT / "install" / "templates" / "user-docs" / "guides" / "production-auth.md"
)
README_DEPLOY = REPO_ROOT / "install" / "templates" / "deploy" / "README.deploy.md"
WEB_DEPLOY_LIVE = REPO_ROOT / "user-docs" / "guides" / "web-deployment.md"
WEB_DEPLOY_TEMPLATE = (
    REPO_ROOT / "install" / "templates" / "user-docs" / "guides" / "web-deployment.md"
)
TRAEFIK_STATIC = REPO_ROOT / "install" / "templates" / "deploy" / "traefik" / "traefik.yml"
TRAEFIK_DYNAMIC = REPO_ROOT / "install" / "templates" / "deploy" / "traefik" / "dynamic.yml"

_YAML_FENCE = re.compile(r"```ya?ml\n(.*?)```", re.DOTALL)


def _guides() -> tuple[Path, ...]:
    return (LIVE_GUIDE, TEMPLATE_GUIDE)


def test_e8_s02_live_and_template_production_auth_match() -> None:
    """Install template stays in lockstep with the live guide."""
    live = LIVE_GUIDE.read_text(encoding="utf-8")
    template = TEMPLATE_GUIDE.read_text(encoding="utf-8")
    assert live == template, "user-docs and install/templates production-auth.md must match"


def test_e8_s02_ac1_traefik_is_reference_pattern() -> None:
    """AC-1: production-auth.md exists with Traefik as the reference pattern."""
    for path in _guides():
        text = path.read_text(encoding="utf-8")
        assert path.is_file(), path
        assert "Traefik" in text, path
        assert "reference" in text.lower(), path
        assert "proxy-only" in text.lower() or "proxy only" in text.lower(), path
        assert "Hayhooks" in text and "no built-in auth" in text.lower(), path
        assert "serve.auth" in text, path


def test_e8_s02_ac2_rest_mcp_chainlit_paths() -> None:
    """AC-2: REST, MCP, and Chainlit path routing are documented."""
    for path in _guides():
        text = path.read_text(encoding="utf-8")
        assert "/v1/chat/completions" in text, path
        assert "/mcp" in text, path
        assert "/chat" in text, path
        assert "1416" in text, path
        assert "1417" in text, path


def test_e8_s02_ac3_traefik_static_dynamic_yaml() -> None:
    """AC-3: example Traefik static/dynamic config with TLS, Headers, ForwardAuth."""
    for path in _guides():
        text = path.read_text(encoding="utf-8")
        assert "entryPoints" in text, path
        assert "certificatesResolvers" in text, path
        assert "forwardAuth" in text, path
        assert "headers:" in text, path
        assert "stsSeconds" in text, path
        blocks = _YAML_FENCE.findall(text)
        assert blocks, f"expected fenced YAML in {path}"
        for block in blocks:
            parsed = yaml.safe_load(block)
            assert parsed is not None, f"empty YAML fence in {path}"

    for snippet in (TRAEFIK_STATIC, TRAEFIK_DYNAMIC):
        parsed = yaml.safe_load(snippet.read_text(encoding="utf-8"))
        assert isinstance(parsed, dict), snippet


def test_e8_s02_ac4_readme_deploy_links_guide() -> None:
    """AC-4: README.deploy.md links the guide and notes Hayhooks has no built-in auth."""
    text = README_DEPLOY.read_text(encoding="utf-8")
    assert "production-auth.md" in text
    assert "no built-in auth" in text.lower()
    assert "Traefik" in text
    assert "traefik/" in text
    assert "serve.auth" in text or "no `serve.auth`" in text


def test_e8_s02_ac5_nginx_caddy_alternatives() -> None:
    """AC-5: Nginx and Caddy documented as optional proxy-only alternatives."""
    for path in _guides():
        text = path.read_text(encoding="utf-8")
        assert "Nginx" in text, path
        assert "Caddy" in text, path
        assert "auth_request" in text, path
        assert "forward_auth" in text, path


def test_e8_s02_web_deployment_cross_link() -> None:
    """E7-S08 reverse link: web-deployment.md points at the production-auth guide."""
    for path in (WEB_DEPLOY_LIVE, WEB_DEPLOY_TEMPLATE):
        text = path.read_text(encoding="utf-8")
        assert "production-auth.md" in text, path

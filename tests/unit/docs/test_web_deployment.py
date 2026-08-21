# Story: E7-S08 / E7.8
"""E7-S08 — Web client deployment layouts (docs content assertions)."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
LIVE_WEB_DEPLOY = REPO_ROOT / "user-docs" / "guides" / "web-deployment.md"
TEMPLATE_WEB_DEPLOY = (
    REPO_ROOT / "install" / "templates" / "user-docs" / "guides" / "web-deployment.md"
)


def _guides() -> tuple[Path, ...]:
    return (LIVE_WEB_DEPLOY, TEMPLATE_WEB_DEPLOY)


def test_e7_s08_live_and_template_web_deployment_match() -> None:
    """Install template stays in lockstep with the live guide."""
    live = LIVE_WEB_DEPLOY.read_text(encoding="utf-8")
    template = TEMPLATE_WEB_DEPLOY.read_text(encoding="utf-8")
    assert live == template, "user-docs and install/templates web-deployment.md must match"


def test_e7_s08_ac2_open_webui_two_container_section() -> None:
    """AC-2: document Open WebUI + Hayhooks two-container pattern."""
    for path in _guides():
        text = path.read_text(encoding="utf-8")
        assert "## Open WebUI + Hayhooks (two containers)" in text, path
        assert "OPENAI_API_BASE_URL" in text, path
        assert "http://hayhooks:1416/v1" in text, path
        assert "ghcr.io/open-webui/open-webui" in text, path
        assert "/v1/models" in text, path
        assert "/docs" in text, path


def test_e7_s08_ac3_spa_nginx_proxy_section() -> None:
    """AC-3: document custom SPA + Nginx proxy pattern."""
    for path in _guides():
        text = path.read_text(encoding="utf-8")
        assert "## Custom SPA + Nginx proxy" in text, path
        assert "proxy_pass http://127.0.0.1:1416/v1/" in text, path
        assert "location /api/v1/" in text, path
        assert 'baseURL: "/api/v1"' in text or "baseURL = \"/api/v1\"" in text, path
        assert "/v1/models" in text, path
        assert "/docs" in text, path


def test_e7_s08_ac4_nextjs_colocated_section() -> None:
    """AC-4: document Next.js co-located pattern."""
    for path in _guides():
        text = path.read_text(encoding="utf-8")
        assert "## Next.js co-located" in text, path
        assert ":3000" in text, path
        assert "localhost:1416" in text or "127.0.0.1:1416" in text, path
        assert "OPENAI_BASE_URL=http://127.0.0.1:1416/v1" in text, path
        assert "app/api/chat/route.ts" in text, path
        assert "/v1/models" in text, path
        assert "/docs" in text, path


def test_e7_s08_ac5_baseurl_points_at_harness_not_openai() -> None:
    """AC-5: OpenAI baseURL examples point at the harness, not api.openai.com."""
    for path in _guides():
        text = path.read_text(encoding="utf-8")
        assert "baseURL" in text or "base_url" in text, path
        assert "http://127.0.0.1:1416/v1" in text, path
        assert "https://api.openai.com/v1" in text, path
        assert "not" in text.lower() and "api.openai.com" in text, path
        # No recipe should set the client at OpenAI's API as the harness backend.
        assert "base_url=\"https://api.openai.com" not in text, path
        assert "baseURL: \"https://api.openai.com" not in text, path
        assert "OPENAI_API_BASE_URL: https://api.openai.com" not in text, path
        assert "OPENAI_BASE_URL=https://api.openai.com" not in text, path

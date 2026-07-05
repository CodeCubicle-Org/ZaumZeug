"""Add ### Implementation resources sections to epic story files."""
from __future__ import annotations

import re
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "docs" / "stories" / "epic-stories"

# Markdown blocks inserted after ### References (before next ### heading).
RESOURCES: dict[str, str] = {
    "01-story.md": """
### Implementation resources

**Libraries & docs**

- [Python packaging — pyproject.toml](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/)
- [Python argparse subcommands](https://docs.python.org/3/library/argparse.html#sub-commands)
- [Architecture §4.4 — illustrative `pyproject.toml`](../../architecture/03-technology-stack.md#44-pyprojecttoml-dependency-groups-phase-1-stub)

**Code sketch — CLI entry**

```python
# src/zaumzeug/cli.py
def main() -> None:
    parser = argparse.ArgumentParser(prog="zaumzeug")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor")
    sub.add_parser("serve")
    # ...
    args = parser.parse_args()
```
""",
    "02-story.md": """
### Implementation resources

**Libraries & docs**

- [Pydantic v2 models](https://docs.pydantic.dev/latest/concepts/models/)
- [Pydantic validation errors](https://docs.pydantic.dev/latest/concepts/validation_errors/)
- [PyYAML safe_load](https://pyyaml.org/wiki/PyYAMLDocumentation)
- [Architecture §6.6 — Phase 1 YAML examples](../../architecture/05-configuration.md#66-phase-1-config-schema)
- [Ideation — full multi-phase YAML](../../ideation-stage.md)

**Code sketch — loader**

```python
from pathlib import Path
import yaml
from zaumzeug.config.schemas import HarnessConfig

def load_harness(path: Path) -> HarnessConfig:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return HarnessConfig.model_validate(data)
```
""",
    "03-story.md": """
### Implementation resources

**Internal spec**

- [Architecture §6.1 — deep-merge rules](../../architecture/05-configuration.md#61-model-registry-merge)
- [Architecture §3.3.1 — model file naming](../../architecture/02-repository-and-layout.md#331-model-config-files-naming)

**Code sketch — recursive merge**

```python
def deep_merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for key, val in override.items():
        if isinstance(val, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], val)
        else:
            out[key] = val
    return out
```
""",
    "04-story.md": """
### Implementation resources

**Internal spec**

- [Architecture §5.2 — runtime vs compile resolution](../../architecture/04-data-flows.md#52-runtime-agent-resolution)
- [Architecture §2.1 — golden rules (no DSPy on serve)](../../architecture/01-overview-and-principles.md#21-golden-rules)
""",
    "05.1-story.md": """
### Implementation resources

**Libraries & docs**

- [python-dotenv](https://pypi.org/project/python-dotenv/) (optional; stdlib `.env` parsing OK)
- [Architecture §13 — debug/doctor patterns](../../architecture/10-operations-and-reference.md#13-debug-and-test-architecture)

**Code sketch — check result**

```python
@dataclass
class CheckResult:
    name: str
    severity: Literal["pass", "warn", "fail"]
    message: str
```
""",
    "05.2-story.md": """
### Implementation resources

**Internal spec**

- [Architecture §6.2 — phase-gated sections](../../architecture/05-configuration.md#62-config-sections)
- [Architecture §5.4 — workflow diagram staleness](../../architecture/04-data-flows.md#54-workflow-diagram-compile)
- [uv package manager](https://docs.astral.sh/uv/) (MCP stdio servers often launched via `uv`)
""",
    "05.3-story.md": """
### Implementation resources

**Internal spec**

- [Architecture §10.3 — deploy `manifest.json`](../../architecture/07-deploy-packaging.md#103-deploy-manifestjson)
- [Architecture §8.1 — deploy source root](../../architecture/06-runtime-and-protocols.md#81-source-roots)
""",
    "06-story.md": """
### Implementation resources

**Internal spec**

- [Architecture §8.2 — serve layering](../../architecture/06-runtime-and-protocols.md#82-harness-vs-raw-hayhooks)
- Reuse config loader + resolver from [E2-S03](04-story.md); no Hayhooks bind on dry-run path
""",
    "07-story.md": """
### Implementation resources

**Libraries & docs**

- [Python logging](https://docs.python.org/3/library/logging.html)
- [Haystack logging](https://docs.haystack.deepset.ai/docs/logging) (wire level when `--verbose`)
- [Architecture §13.2 — `HARNESS_LOG_LEVEL`](../../architecture/10-operations-and-reference.md#132-mechanisms)
""",
    "08-story.md": """
### Implementation resources

**Config examples**

- [Architecture §6.6 — `workflow.yaml` example](../../architecture/05-configuration.md#66-phase-1-config-schema)
- [User guide — multi-agent workflow](../../../install/templates/user-docs/guides/multi-agent-workflow.md)

**Code sketch — serial stage**

```yaml
# workflow.yaml (Phase 1)
entry: researcher
stages:
  - agent: researcher
```
""",
    "09-story.md": """
### Implementation resources

**Config example — mock profile**

```yaml
# agents-models.yaml
default_model_id: mock
models:
  mock:
    provider: mock
    model: harness-fixture
```

- [Architecture §6.6 — example harness mock setup](../../architecture/05-configuration.md#66-phase-1-config-schema)
- [Architecture §13.2 — mock profile mechanism](../../architecture/10-operations-and-reference.md#132-mechanisms)
""",
    "10-story.md": """
### Implementation resources

**Libraries & docs**

- [Haystack Chat Generators](https://docs.haystack.deepset.ai/docs/chatgenerators)
- [openrouter-haystack](https://pypi.org/project/openrouter-haystack/)
- [openai-haystack](https://pypi.org/project/openai-haystack/) · [anthropic-haystack](https://pypi.org/project/anthropic-haystack/)
- [LiteLLM provider strings](https://docs.litellm.ai/docs/providers) (compile-time LM wiring in Phase 2)
- [Architecture §7 — ModelRouter](../../architecture/05-configuration.md#7-model-routing)

**Code sketch — provider map**

```python
PROVIDERS = {
    "mock": ("zaumzeug.integrations.mock", "MockChatGenerator"),
    "openrouter": ("haystack_integrations.components.generators.openrouter", "OpenRouterChatGenerator"),
}
```
""",
    "11-story.md": """
### Implementation resources

**Libraries & docs**

- [httpx — HTTP client](https://www.python-httpx.org/) (outbound fetch)
- [respx — mock httpx in tests](https://lundberg.github.io/respx/)
- [Haystack `@component` tools](https://docs.haystack.deepset.ai/docs/custom-components)
- [Architecture §6.5 — `web_fetch` limits](../../architecture/05-configuration.md#65-builtin-tools-catalog)

**Code sketch — SSRF guard**

```python
import ipaddress, socket
def is_public_host(host: str) -> bool:
    ip = ipaddress.ip_address(socket.gethostbyname(host))
    return not (ip.is_private or ip.is_loopback or ip.is_link_local)
```
""",
    "12-story.md": """
### Implementation resources

**Libraries & docs**

- [Haystack Agents](https://docs.haystack.deepset.ai/docs/agents)
- [Haystack Agent — running tools](https://docs.haystack.deepset.ai/docs/agents#adding-tools-to-an-agent)
- [Hayhooks](https://docs.haystack.deepset.ai/docs/hayhooks)
- [Architecture §2.3 — agent loop mapping](../../architecture/01-overview-and-principles.md#23-harness-layer-mapping-guides-and-sensors)

**Code sketch — factory**

```python
from haystack.components.agents import Agent

def build_agent(*, chat_generator, tools, system_prompt: str) -> Agent:
    return Agent(chat_generator=chat_generator, tools=tools, system_prompt=system_prompt)
```
""",
    "13-story.md": """
### Implementation resources

**Libraries & docs**

- [Hayhooks](https://docs.haystack.deepset.ai/docs/hayhooks)
- [Hayhooks OpenAI-compatible endpoints](https://docs.haystack.deepset.ai/docs/hayhooks#openai-compatible-endpoints)
- [OpenAI Chat Completions API](https://platform.openai.com/docs/api-reference/chat)
- [Architecture §9.1 — protocol selection](../../architecture/06-runtime-and-protocols.md#91-protocol-selection)
- [Architecture §14 — localhost bind Phase 1](../../architecture/10-operations-and-reference.md#14-security-phase-1-stance)

**Test client sketch**

```python
import httpx
r = httpx.post(f"{base}/v1/chat/completions", json={
    "model": "mock", "messages": [{"role": "user", "content": "hi"}]
})
```
""",
    "14-story.md": """
### Implementation resources

**Config templates**

- [Architecture §6.6 — full `example` harness tree](../../architecture/05-configuration.md#66-phase-1-config-schema)
- [Ideation — reference YAML](../../ideation-stage.md)
- Copy targets: `usr-harnesses/example/`, `install/templates/usr-harnesses/example/`
""",
    "15-story.md": """
### Implementation resources

**Libraries & docs**

- [pytest](https://docs.pytest.org/) · [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [Architecture §13.3 — test pyramid layout](../../architecture/10-operations-and-reference.md#133-test-pyramid)
- [Architecture §13.6 — testing playbook](../../architecture/10-operations-and-reference.md#136-testing-playbook)
- [User guide — testing](../../../install/templates/user-docs/guides/testing.md)
- [debugpy — IDE attach](https://github.com/microsoft/debugpy)
""",
    "16-story.md": """
### Implementation resources

**Libraries & docs**

- [OpenAI Chat Completions — response shape](https://platform.openai.com/docs/api-reference/chat/object)
- [httpx](https://www.python-httpx.org/) · [pytest-httpx / respx](https://lundberg.github.io/respx/) for stubbing `web_fetch`
- [Architecture §9.4 — OpenAI-compatible layouts](../../architecture/06-runtime-and-protocols.md#94-web-deployment-layouts)

**Minimal response shape to assert**

```json
{"choices": [{"message": {"role": "assistant", "content": "..."}}]}
```
""",
    "17-story.md": """
### Implementation resources

**Internal spec**

- [Architecture §8.2 — `zaumzeug run`](../../architecture/06-runtime-and-protocols.md#82-harness-vs-raw-hayhooks)
- [User guide — multi-agent workflow](../../../install/templates/user-docs/guides/multi-agent-workflow.md)
- [Haystack Agent messages](https://docs.haystack.deepset.ai/docs/agents) (list of `{"role", "content"}` dicts)

**Inter-stage context (AC-3)**

```python
messages = [{"role": "user", "content": user_input}]
if prior_output:
    messages.insert(0, {"role": "user", "content": prior_output})
```
""",
    "18-story.md": """
### Implementation resources

**Libraries & docs**

- [venv — Python 3.11+](https://docs.python.org/3/library/venv.html)
- [pip editable install](https://pip.pypa.io/en/stable/cli/pip_install/#cmdoption-e)
- [Architecture §3.4 — `client_install.py`](../../architecture/02-repository-and-layout.md#34-install-scripts-dev-vs-target)
- [Architecture §4.4 — `pip install -e ".[dev]"`](../../architecture/03-technology-stack.md#44-pyprojecttoml-dependency-groups-phase-1-stub)
""",
    "19-story.md": """
### Implementation resources

**Internal spec**

- [Architecture §3.4 — install wrappers](../../architecture/02-repository-and-layout.md#34-install-scripts-dev-vs-target)
- Mirror pattern from `install/client_install.py` → `install.sh` / `install.ps1` forwarding args
""",
    "20-story.md": """
### Implementation resources

**Scaffold sources**

- [Architecture §6.6 — Phase 1 harness layout](../../architecture/05-configuration.md#66-phase-1-config-schema)
- [E3-S04 example templates](14-story.md) — copy from `usr-harnesses/example/`
- [Ideation — full tree reference](../../ideation-stage.md)
""",
    "21-story.md": """
### Implementation resources

**Internal spec**

- [Architecture §3.3 — harness folder layout](../../architecture/02-repository-and-layout.md#33-harness-folder-layout)
- Reuse scaffolding logic from [E1-S03](20-story.md) / `client_install.py`
""",
    "22-story.md": """
### Implementation resources

**Templates**

- [Architecture §3.5 — user-docs layout](../../architecture/02-repository-and-layout.md#35-user-documentation)
- [Architecture §13.6 — testing guide template](../../architecture/10-operations-and-reference.md#136-testing-playbook)
- Seed from `install/templates/user-docs/`
""",
    "23-story.md": """
### Implementation resources

**Internal spec**

- [PRD §7.4 — user installation guide content](../../prd.md#74-user-installation-guide-content-for-readme--phase-1)
- Link to [Architecture hub](../../architecture.md) and [stories index](../00-README.md)
""",
    "24-story.md": """
### Implementation resources

**Libraries & docs**

- [GitHub Actions — matrix strategy](https://docs.github.com/en/actions/using-jobs/using-a-matrix-for-your-jobs)
- [actions/setup-python](https://github.com/actions/setup-python)
- [pytest in CI](https://docs.pytest.org/en/stable/how-to/usage.html)
- [Architecture §13.6 — mock-first CI](../../architecture/10-operations-and-reference.md#136-testing-playbook)
""",
    "26-story.md": """
### Implementation resources

**Libraries & docs**

- [DSPy modules](https://dspy.ai/learn/programming/modules/)
- [DSPy signatures](https://dspy.ai/learn/programming/signatures/)
- [Architecture §4.2 — DSPy compile-time only](../../architecture/03-technology-stack.md#42-library-boundaries-when-to-use-what)

**Code sketch**

```python
import importlib
mod = importlib.import_module("usr_harnesses.example.modules.researcher")
dspy_module = mod.ResearchModule()
```
""",
    "27.1-story.md": """
### Implementation resources

**Libraries & docs**

- [DSPy configuration / LM setup](https://dspy.ai/learn/programming/language_models/)
- [Architecture §6.2 — `compile` section](../../architecture/05-configuration.md#62-config-sections)
- [Pydantic model validators](https://docs.pydantic.dev/latest/concepts/validators/)
""",
    "27.2-story.md": """
### Implementation resources

**Libraries & docs**

- [DSPy GEPA optimizer](https://dspy.ai/api/optimizers/GEPA/overview/)
- [GEPA (gepa-ai)](https://github.com/gepa-ai/gepa)
- [Architecture §4.2 — GEPA boundaries](../../architecture/03-technology-stack.md#42-library-boundaries-when-to-use-what)
- [Architecture §12 Pattern A](../../architecture/08-compile-and-optimization.md#pattern-a-default-phase-2-v1)

**Metric sketch (AC-3)**

```python
def metric(example, pred, trace=None):
    score = 1.0 if "expected" in pred.answer else 0.0
    feedback = "Include expected keyword in answer." if score < 1 else "Good."
    return dspy.Prediction(score=score, feedback=feedback)
```
""",
    "28.1-story.md": """
### Implementation resources

**Libraries & docs**

- [DSPy `dump_state()`](https://dspy.ai/) (module state export)
- [syrupy — snapshot tests](https://github.com/syrupy-project/syrupy) (optional; AC-7 golden files)
- [Architecture §5.3 — artifact layout](../../architecture/04-data-flows.md#53-artifact-layout)

**Manifest sketch**

```json
{
  "run_id": "20260705T120000Z",
  "paths": {"system_prompt": "prompts/system.md", "input_rewrite": "prompts/input_rewrite.md"}
}
```
""",
    "28.2-story.md": """
### Implementation resources

**Internal spec**

- [Architecture §12 Pattern A — input rewrite](../../architecture/08-compile-and-optimization.md#pattern-a-default-phase-2-v1)
- [Jinja2](https://jinja.palletsprojects.com/) if template variables needed in preprocess
""",
    "30-story.md": """
### Implementation resources

**Internal spec**

- [Architecture §5.2 — artifact > system_prompt priority](../../architecture/04-data-flows.md#52-runtime-agent-resolution)
- [E4-S03b preprocess](28.2-story.md) — no `import dspy` on serve path
""",
    "31-story.md": """
### Implementation resources

**Internal spec**

- Same validation path as [E4-S02a](27.1-story.md) without invoking GEPA or writing artifacts
""",
    "32-story.md": """
### Implementation resources

**Internal spec**

- [Architecture §5.3 — pinned `run_id` folders](../../architecture/04-data-flows.md#53-artifact-layout)
- Update `agent.yaml` / harness config to point `artifact:` at chosen run directory
""",
    "33-story.md": """
### Implementation resources

**Internal spec**

- [Architecture §5.4 — workflow diagram at compile](../../architecture/04-data-flows.md#54-workflow-diagram-compile)
- [Mermaid flowchart syntax](https://mermaid.js.org/syntax/flowchart.html) (if diagram is Mermaid)
""",
    "34-story.md": """
### Implementation resources

**Libraries & docs**

- [DeepEval PyPI](https://pypi.org/project/deepeval/)
- [Architecture §4.4 — `[eval]` extra](../../architecture/03-technology-stack.md#44-pyprojecttoml-dependency-groups-phase-1-stub)
""",
    "35-story.md": """
### Implementation resources

**Libraries & docs**

- [DeepEval docs](https://docs.confident-ai.com/)
- [DeepEval metrics](https://docs.confident-ai.com/docs/metrics-introduction)
- [Architecture §6.3 — eval frameworks](../../architecture/05-configuration.md#63-zaumzeug-eval-frameworks)
""",
    "36-story.md": """
### Implementation resources

**Internal spec**

- Implementation owner: [E5-S06](46-story.md) — this story is traceability only
- [Architecture §6.4 — deploy eval gate](../../architecture/05-configuration.md#64-deploy-eval-gate)
""",
    "37-story.md": """
### Implementation resources

**Libraries & docs**

- [DeepEval pytest integration](https://docs.confident-ai.com/docs/testing-pytest)
- [pytest markers](https://docs.pytest.org/en/stable/example/markers.html) for optional `[eval]` jobs
""",
    "38-story.md": """
### Implementation resources

**Libraries & docs**

- [DeepEval — trace to test case](https://docs.confident-ai.com/docs/evaluation-datasets)
- [Architecture §5.5 — improvement loop](../../architecture/04-data-flows.md#55-continuous-improvement-loop)
""",
    "39-story.md": """
### Implementation resources

**Libraries & docs**

- [httpx](https://www.python-httpx.org/) — HTTP black-box against running serve
- [DeepEval — Mode C](../../architecture/05-configuration.md#63-zaumzeug-eval-frameworks)
""",
    "40-story.md": """
### Implementation resources

**Internal spec**

- [Architecture §6.3 — GEPA ↔ DeepEval bridge](../../architecture/05-configuration.md#63-zaumzeug-eval-frameworks)
- Reuse GEPA textual feedback format from [E4-S02b](27.2-story.md)
""",
    "41-story.md": """
### Implementation resources

**Internal spec**

- [Architecture §10.2 — packager steps](../../architecture/07-deploy-packaging.md#102-packager-steps)
- [Architecture §10.3 — `manifest.json` schema](../../architecture/07-deploy-packaging.md#103-deploy-manifestjson)
- [E5-S02 copy rules](42-story.md)
""",
    "42-story.md": """
### Implementation resources

**Internal spec**

- [Architecture §10.1 — dev vs deploy copy matrix](../../architecture/07-deploy-packaging.md#101-dev-vs-deploy)
- Golden tests: `tests/unit/deploy/test_copy_rules.py` (shared with E7-S02, E8-S01)
""",
    "43-story.md": """
### Implementation resources

**Internal spec**

- [Architecture §8.1 — `HARNESS_ROOT` / `--deploy`](../../architecture/06-runtime-and-protocols.md#81-source-roots)
- Reuse [E3-S02 serve runner](13-story.md) with deploy path resolution
""",
    "44-story.md": """
### Implementation resources

**Internal spec**

- [Architecture §2.5 — env over convention](../../architecture/01-overview-and-principles.md#25-cross-platform-portability)

```bash
HARNESS_ROOT=deploy zaumzeug serve my-harness --deploy
```
""",
    "45-story.md": """
### Implementation resources

**Internal spec**

- [Architecture §10.5 — production dependencies](../../architecture/07-deploy-packaging.md#105-production-server-dependencies)
- [E5-S09c target install verify](49.3-story.md)
""",
    "46-story.md": """
### Implementation resources

**Libraries & docs**

- [DeepEval CLI / thresholds](https://docs.confident-ai.com/)
- [Architecture §6.4 — deploy eval gate](../../architecture/05-configuration.md#64-deploy-eval-gate)
- Requires [E6-S02](35-story.md) `zaumzeug eval` before gate can run

**Config example**

```yaml
deploy:
  eval_gate: block   # skip | warn | block
```
""",
    "47-story.md": """
### Implementation resources

**Internal spec**

- [Architecture §10.4 — deploy git policy](../../architecture/07-deploy-packaging.md#104-git-and-gitignore)
- `.gitignore` patterns for `deploy/` generated bundles
""",
    "48-story.md": """
### Implementation resources

**Internal spec**

- [Architecture §10.6 — platform targets matrix](../../architecture/07-deploy-packaging.md#106-deploy-platform-targets)
- [GitHub Actions runners](https://docs.github.com/en/actions/using-github-hosted-runners)
""",
    "49.1-story.md": """
### Implementation resources

**Libraries & docs**

- [venv](https://docs.python.org/3/library/venv.html) · [pip install zaumzeug](https://pip.pypa.io/)
- [Architecture §10.7 — target install script](../../architecture/07-deploy-packaging.md#107-target-runtime-install-script)
- Mirror dev install patterns from [E1-S01](18-story.md) (runtime-only deps)
""",
    "49.2-story.md": """
### Implementation resources

**Internal spec**

- [E1-S02 install wrappers](19-story.md) — same forward-args pattern for `target-install.sh` / `.ps1`
""",
    "49.3-story.md": """
### Implementation resources

**Internal spec**

- [E2-S04c doctor --deploy](05.3-story.md)
- [E2-S05 serve --dry-run](06-story.md)

```bash
python install/target_install.py --verify --name example
```
""",
    "50-story.md": """
### Implementation resources

**Libraries & docs**

- [Model Context Protocol](https://modelcontextprotocol.io/introduction)
- [Haystack MCPToolset](https://docs.haystack.deepset.ai/docs/mcp)
- [uv — MCP server launcher](https://docs.astral.sh/uv/)
- [Architecture §9.2 — MCP when to use](../../architecture/06-runtime-and-protocols.md#92-mcp-when-to-use)

**Config sketch**

```yaml
tools:
  mcp:
    - name: filesystem
      command: uv
      args: ["run", "mcp-server-filesystem", "/workspace"]
```
""",
    "51-story.md": """
### Implementation resources

**Libraries & docs**

- [Haystack custom components / tools](https://docs.haystack.deepset.ai/docs/custom-components)
- [Architecture §3.3 — `agents/<name>/tools/`](../../architecture/02-repository-and-layout.md#33-harness-folder-layout)

**Tool sketch**

```python
from haystack.tools import Tool

def search_docs(query: str) -> str: ...

search_tool = Tool(name="search_docs", function=search_docs, description="...")
```
""",
    "52-story.md": """
### Implementation resources

**Libraries & docs**

- [Cursor MCP docs](https://docs.cursor.com/context/model-context-protocol)
- [MCP JSON config](https://modelcontextprotocol.io/quickstart/user) (`.cursor/mcp.json`)
- Scaffold template from [E1-S03](20-story.md)
""",
    "53-story.md": """
### Implementation resources

**Libraries & docs**

- [Chainlit](https://docs.chainlit.io/)
- [Hayhooks Chainlit extra](https://docs.haystack.deepset.ai/docs/hayhooks) — `pip install "hayhooks[chainlit]"`
- [Architecture §9.4 — embedded UI layout](../../architecture/06-runtime-and-protocols.md#94-web-deployment-layouts)
""",
    "54-story.md": """
### Implementation resources

**Libraries & docs**

- [Agent Client Protocol](https://agentclientprotocol.com/)
- [Architecture §9.3 — ACP when to use](../../architecture/06-runtime-and-protocols.md#93-acp-when-to-use)
""",
    "55-story.md": """
### Implementation resources

**Internal spec**

- [E5-S03 serve --deploy](43-story.md) — MCP from deploy bundle uses production paths
- [E7-S01 MCP config](50-story.md)
""",
    "56-story.md": """
### Implementation resources

**Internal spec**

- [Architecture §6.5 — extended builtins catalog](../../architecture/05-configuration.md#65-builtin-tools-catalog)
- Extend [E3-S03 web_fetch](11-story.md) catalog registration pattern
""",
    "57-story.md": """
### Implementation resources

**Internal spec**

- [Architecture §9.4 — web deployment layouts](../../architecture/06-runtime-and-protocols.md#94-web-deployment-layouts)
- Cross-link Chainlit ([E7-S04](53-story.md)) and ACP ([E7-S05](54-story.md)) setup guides
""",
    "58-story.md": """
### Implementation resources

**Libraries & docs**

- [Haystack Pipelines](https://docs.haystack.deepset.ai/docs/pipelines)
- [Architecture §10.1 — pipeline copy rules](../../architecture/07-deploy-packaging.md#101-dev-vs-deploy)

**Config sketch**

```yaml
serve:
  expose:
    - id: rag_pipeline
      path: pipelines/rag.yaml
```
""",
    "59-story.md": """
### Implementation resources

**Libraries & docs**

- [Traefik ForwardAuth](https://doc.traefik.io/traefik/middlewares/http/forwardauth/)
- [Traefik Headers middleware](https://doc.traefik.io/traefik/middlewares/http/headers/)
- [Architecture §14 — proxy-only auth Phase 4](../../architecture/10-operations-and-reference.md#14-security-phase-1-stance)
""",
    "60-story.md": """
### Implementation resources

**Libraries & docs**

- [DeepEval datasets](https://docs.confident-ai.com/docs/evaluation-datasets)
- [Architecture §5.5 — trace → dataset loop](../../architecture/04-data-flows.md#55-continuous-improvement-loop)
""",
    "62-story.md": """
### Implementation resources

**Libraries & docs**

- [Dockerfile reference](https://docs.docker.com/reference/dockerfile/)
- [Architecture §10.6 — container targets](../../architecture/07-deploy-packaging.md#106-deploy-platform-targets)
- [E8-S02 Traefik auth](59-story.md) for production compose examples
""",
    "63-story.md": """
### Implementation resources

**Libraries & docs**

- [DeepEval `@observe` decorator](https://docs.confident-ai.com/docs/tracing)
- [Confident AI](https://www.confident-ai.com/docs)
- [Architecture §6.3 — Mode B tracing](../../architecture/05-configuration.md#63-zaumzeug-eval-frameworks)
""",
}


def insert_resources(text: str, block: str) -> str:
    if "### Implementation resources" in text:
        return text
    block = block.strip() + "\n"
    # Insert after References section (bullets until next ### heading)
    m = re.search(r"(### References\n(?:.*?\n)*?)(?=### )", text, re.DOTALL)
    if m:
        insert_at = m.end(1)
        return text[:insert_at] + "\n" + block + "\n" + text[insert_at:]
    # Fallback: before Acceptance criteria
    m2 = re.search(r"(### Acceptance criteria)", text)
    if m2:
        return text[: m2.start()] + block + "\n" + text[m2.start() :]
    return text


def build_hub_index() -> str:
    lines = [
        "# Implementation resources — index",
        "",
        "Per-story **Implementation resources** sections link library docs, architecture examples, and minimal code sketches. This index groups the same links by technology.",
        "",
        "| Technology | Documentation | Used in stories |",
        "|---|---|---|",
        "| **Haystack / Hayhooks** | [Agents](https://docs.haystack.deepset.ai/docs/agents) · [Hayhooks](https://docs.haystack.deepset.ai/docs/hayhooks) · [Pipelines](https://docs.haystack.deepset.ai/docs/pipelines) · [MCP](https://docs.haystack.deepset.ai/docs/mcp) | E3-S00–S03, E7, E8-S01 |",
        "| **OpenAI REST** | [Chat Completions API](https://platform.openai.com/docs/api-reference/chat) | E3-S02, E3-S07 |",
        "| **Pydantic / YAML** | [Pydantic v2](https://docs.pydantic.dev/latest/) · [PyYAML](https://pyyaml.org/wiki/PyYAMLDocumentation) | E2-S01, E2-S07 |",
        "| **DSPy / GEPA** | [DSPy modules](https://dspy.ai/learn/programming/modules/) · [GEPA](https://dspy.ai/api/optimizers/GEPA/overview/) · [gepa-ai](https://github.com/gepa-ai/gepa) | E4-S01, E4-S02a/b |",
        "| **DeepEval** | [Docs](https://docs.confident-ai.com/) | E6, E8-S06 |",
        "| **MCP / ACP** | [MCP](https://modelcontextprotocol.io/) · [ACP](https://agentclientprotocol.com/) · [Cursor MCP](https://docs.cursor.com/context/model-context-protocol) | E7 |",
        "| **Testing** | [pytest](https://docs.pytest.org/) · [httpx](https://www.python-httpx.org/) · [respx](https://lundberg.github.io/respx/) · [syrupy](https://github.com/syrupy-project/syrupy) | E1-S07, E3-S06/S07, E4-S03a |",
        "| **Packaging / CI** | [pyproject.toml](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/) · [GitHub Actions matrix](https://docs.github.com/en/actions/using-jobs/using-a-matrix-for-your-jobs) | E2-S00, E1-S01/S07 |",
        "| **Deploy / ops** | [Traefik ForwardAuth](https://doc.traefik.io/traefik/middlewares/http/forwardauth/) · [Dockerfile](https://docs.docker.com/reference/dockerfile/) | E5, E8 |",
        "",
        "**Canonical config YAML:** [Architecture §6.6](../../architecture/05-configuration.md#66-phase-1-config-schema) · [Ideation archive](../../ideation-stage.md)",
        "",
        "See also [Architecture §16 — ecosystem links](../../architecture/10-operations-and-reference.md#16-supporting-ecosystem-reference).",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    updated = 0
    for filename, block in RESOURCES.items():
        path = OUT / filename
        if not path.exists():
            print(f"Skip missing {filename}")
            continue
        text = path.read_text(encoding="utf-8")
        new_text = insert_resources(text, block)
        if new_text != text:
            path.write_text(new_text, encoding="utf-8")
            updated += 1
            print(f"Updated {filename}")

    hub = OUT / "00-implementation-resources.md"
    hub.write_text(build_hub_index(), encoding="utf-8")
    print(f"Wrote {hub.name}")

    readme = OUT / "00-README.md"
    if readme.exists():
        text = readme.read_text(encoding="utf-8")
        link = "[Implementation resources index](00-implementation-resources.md)"
        if link not in text:
            text = text.replace(
                "| **Related** | [Epic index](../00-README.md) · [PRD](../../prd.md) |",
                "| **Related** | [Epic index](../00-README.md) · [PRD](../../prd.md) · "
                "[Implementation resources](00-implementation-resources.md) |",
            )
            readme.write_text(text, encoding="utf-8")
            print("Updated 00-README.md")

    print(f"Done — {updated} stories updated")


if __name__ == "__main__":
    main()

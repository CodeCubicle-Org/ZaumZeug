# Implementation resources — index

Per-story **Implementation resources** sections link library docs, architecture examples, and minimal code sketches. This index groups the same links by technology.

| Technology | Documentation | Used in stories |
|---|---|---|
| **Haystack / Hayhooks** | [Agents](https://docs.haystack.deepset.ai/docs/agents) · [Hayhooks](https://docs.haystack.deepset.ai/docs/hayhooks) · [Pipelines](https://docs.haystack.deepset.ai/docs/pipelines) · [MCP](https://docs.haystack.deepset.ai/docs/mcp) | E3-S00–S03, E7, E8-S01 |
| **OpenAI REST** | [Chat Completions API](https://platform.openai.com/docs/api-reference/chat) | E3-S02, E3-S07 |
| **Pydantic / YAML** | [Pydantic v2](https://docs.pydantic.dev/latest/) · [PyYAML](https://pyyaml.org/wiki/PyYAMLDocumentation) | E2-S01, E2-S07 |
| **DSPy / GEPA** | [DSPy modules](https://dspy.ai/learn/programming/modules/) · [GEPA](https://dspy.ai/api/optimizers/GEPA/overview/) · [gepa-ai](https://github.com/gepa-ai/gepa) · loader: [`compile/module_loader.py`](../../../src/zaumzeug/compile/module_loader.py) ✅ (E4-S01) · CLI/runner: [`compile/runner.py`](../../../src/zaumzeug/compile/runner.py), [`compile/gepa_runner.py`](../../../src/zaumzeug/compile/gepa_runner.py) ✅ (E4-S02a/b) · export: [`compile/export.py`](../../../src/zaumzeug/compile/export.py) ✅ (E4-S03a, 2026-07-28) · preprocess: [`runtime/preprocess.py`](../../../src/zaumzeug/runtime/preprocess.py) ✅ (E4-S03b, 2026-07-28) | E4-S01 ✅, E4-S02a ✅, E4-S02b ✅, E4-S03a ✅, E4-S03b ✅ |
| **DeepEval** | [Docs](https://docs.confident-ai.com/) | E6, E8-S06 |
| **MCP / ACP** | [MCP](https://modelcontextprotocol.io/) · [ACP](https://agentclientprotocol.com/) · [Cursor MCP](https://docs.cursor.com/context/model-context-protocol) | E7 |
| **Testing** | [pytest](https://docs.pytest.org/) · [httpx](https://www.python-httpx.org/) · [respx](https://lundberg.github.io/respx/) · [syrupy](https://github.com/syrupy-project/syrupy) | E1-S07, E3-S06/S07, E4-S03a |
| **Packaging / CI** | [pyproject.toml](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/) · [GitHub Actions matrix](https://docs.github.com/en/actions/using-jobs/using-a-matrix-for-your-jobs) · [ci-matrix.yml](../../../.github/workflows/ci-matrix.yml) ✅ (E1-S07, 2026-07-22) | E2-S00, E1-S01/S02/S07 |
| **Deploy / ops** | [Traefik ForwardAuth](https://doc.traefik.io/traefik/middlewares/http/forwardauth/) · [Dockerfile](https://docs.docker.com/reference/dockerfile/) | E5, E8 |

**Canonical config YAML:** [Architecture §6.6](../../architecture/05-configuration.md#66-phase-1-config-schema) · [Ideation archive](../../ideation-stage.md)

See also [Architecture §16 — ecosystem links](../../architecture/10-operations-and-reference.md#16-supporting-ecosystem-reference).

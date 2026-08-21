# Pipelines and RAG

Expose Haystack YAML under `pipelines/` so batch and RAG flows ship beside the entry agent. Register each pipeline in `harness.yaml` with **`serve.expose`**. ZaumZeug serve then mounts **`POST /{id}/run`** (Architecture §9.1). Listed files are copied into the deploy bundle.

## Register a pipeline

1. Author YAML in **`pipelines/`** (Haystack `components` / `connections`, plus Hayhooks `inputs` / `outputs`).
2. List the id in **`harness.yaml`**:

```yaml
serve:
  hayhooks:
    port: 1416
  expose:
    - id: rag_pipeline
      path: pipelines/rag.yaml
    # shorthand — file pipelines/summarize.yaml
    - summarize
```

String ids resolve to `pipelines/<id>.yaml`. Object form matches the path you actually keep on disk.

3. Optional: add the same id as a **`workflow.yaml`** stage (`- pipeline: rag_pipeline`). `zaumzeug run` invokes that YAML with the workflow input (and prior-stage text as `context`).

The id in **`serve.expose`**, the file under **`pipelines/`**, and any **`workflow.yaml`** `pipeline:` row must match.

## Call over HTTP

With `zaumzeug serve <harness>`:

```bash
curl -s http://127.0.0.1:1416/rag_pipeline/run \
  -H "Content-Type: application/json" \
  -d '{"query":"How many languages are there?"}'
```

The entry agent remains on OpenAI REST (`POST /v1/chat/completions`). Exposed pipelines are the batch / webhook path: **`POST /{pipeline}/run`**.

Hayhooks YAML must declare **`inputs`** and **`outputs`** so the `/run` body maps onto component sockets (for example `query: retriever.query`).

## RAG pattern (retriever → prompt → generator)

A retrieval-augmented generation pipeline is a **fixed graph**: retrieve documents, fill a prompt, then generate. That is the pattern to put in `pipelines/rag.yaml`:

```yaml
components:
  retriever:
    type: haystack.components.retrievers.in_memory.bm25_retriever.InMemoryBM25Retriever
    init_parameters:
      document_store:
        type: haystack.document_stores.in_memory.document_store.InMemoryDocumentStore
        init_parameters: {}
      top_k: 5
  prompt_builder:
    type: haystack.components.builders.prompt_builder.PromptBuilder
    init_parameters:
      required_variables:
        - query
        - documents
      template: |
        Given these documents, answer the question.
        Documents:
        {% for doc in documents %}
          {{ doc.content }}
        {% endfor %}
        Question: {{ query }}
        Answer:
  generator:
    type: haystack.components.generators.openai.OpenAIGenerator
    init_parameters:
      model: gpt-4o-mini
connections:
  - sender: retriever.documents
    receiver: prompt_builder.documents
  - sender: prompt_builder.prompt
    receiver: generator.prompt
inputs:
  query: retriever.query
outputs:
  replies: generator.replies
```

Flow:

1. **Retriever** — BM25 (or embedding) search over the document store.
2. **Prompt** — Jinja template injects `documents` + `query`.
3. **Generator** — LLM completes the filled prompt.

Swap `OpenAIGenerator` for an OpenAI-compatible / OpenRouter chat generator via your usual provider env vars. In-memory stores start empty; ingest documents in a separate pipeline or at process start. For production indexes, replace `InMemoryDocumentStore` with the store you operate.

## `search_docs` builtin

When a RAG pipeline is listed in `serve.expose`, agents can attach **`search_docs`**:

```yaml
# agents/<name>/agent.yaml
tools:
  builtin: [web_fetch, search_docs]
```

The factory loads the RAG-named expose row (`rag` in the id or path, otherwise the first `serve.expose` entry) and registers a Haystack tool that runs that pipeline for a query. Listing `search_docs` without `serve.expose` fails at agent build.

## Deploy

Only pipelines listed in `serve.expose` are copied to `deploy/<name>/pipelines/` (`zaumzeug deploy`). Unlisted YAML under `pipelines/` stays in the dev tree.

## Related

- [Multi-agent workflow](multi-agent-workflow.md) — `pipeline:` stages vs agent stages
- [Custom tools](custom-tools.md) — `search_docs` in the builtin catalog
- [CLI — serve](../reference/cli.md#zaumzeug-serve)
- [Haystack Pipelines](https://docs.haystack.deepset.ai/docs/pipelines)

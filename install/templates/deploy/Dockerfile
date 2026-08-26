# Optional deploy-bundle Dockerfile (E8-S05).
# Build context = this folder (deploy/{{harness_name}}/):
#
#   docker build -t zaumzeug-{{harness_name}} .
#
# Runtime secrets: inject .env at run time — never bake secrets into the image.
#
#   docker run --env-file /path/to/.env -p 1416:1416 zaumzeug-{{harness_name}}
#
# Open WebUI two-container layout: see docker-compose.example.yml and
# user-docs/guides/web-deployment.md. Serve binds 127.0.0.1 in v1 — use host
# networking or Traefik on the same host for multi-container reachability.

FROM python:3.11-slim

WORKDIR /app

# Place the bundle at deploy/<name>/ so `zaumzeug serve --deploy` /
# HARNESS_ROOT=deploy resolve the same layout as a bare-metal target.
COPY . /app/deploy/{{harness_name}}/

# target_install pattern with --skip-venv (image Python is the runtime).
# Runtime-only pip install zaumzeug — no [dev], [eval], DSPy, GEPA, DeepEval.
# .env is excluded via .dockerignore; do not COPY secrets here.
WORKDIR /app/deploy/{{harness_name}}
RUN python target_install.py --skip-venv \
    && rm -f .env /app/.env

WORKDIR /app
ENV HARNESS_ROOT=deploy
EXPOSE 1416

# Documented container CMD (AC-3): production serve from the deploy root.
CMD ["zaumzeug", "serve", "{{harness_name}}", "--deploy"]

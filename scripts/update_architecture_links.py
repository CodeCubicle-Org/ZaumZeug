"""Update architecture.md#anchor links to architecture/ topic files."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"

# anchor -> path under docs/architecture/ (optional #subanchor)
ANCHOR_TO_FILE: dict[str, str] = {
    "221-harness-vs-agent-terminology": "01-overview-and-principles.md",
    "2-architectural-principles": "01-overview-and-principles.md",
    "21-golden-rules": "01-overview-and-principles.md",
    "23-harness-layer-mapping-guides-and-sensors": "01-overview-and-principles.md",
    "25-cross-platform-portability": "01-overview-and-principles.md",
    "3-repository-structure": "02-repository-and-layout.md",
    "31-separation-rules": "02-repository-and-layout.md",
    "32-package-naming": "02-repository-and-layout.md",
    "32-package-naming-working-default": "02-repository-and-layout.md#32-package-naming",
    "33-harness-folder-layout": "02-repository-and-layout.md",
    "331-model-config-files-naming": "02-repository-and-layout.md#331-model-config-files-naming",
    "34-install-scripts-dev-vs-target": "02-repository-and-layout.md",
    "34-install-vs-harness-init": "02-repository-and-layout.md#34-install-scripts-dev-vs-target",
    "35-user-documentation": "02-repository-and-layout.md",
    "4-technology-stack": "03-technology-stack.md",
    "41-core-libraries": "03-technology-stack.md",
    "42-library-boundaries-when-to-use-what": "03-technology-stack.md#42-library-boundaries-when-to-use-what",
    "44-pyprojecttoml-dependency-groups-phase-1-stub": "03-technology-stack.md",
    "45-test-dependencies": "03-technology-stack.md#45-test-dependencies",
    "51-default-pattern-compile--deploy--serve": "04-data-flows.md#51-default-pattern-compile-deploy-serve",
    "pattern-a--default-phase-2-v1": "08-compile-and-optimization.md#pattern-a-default-phase-2-v1",
    "pattern-b--optimize_anything-deferred--phase-4": "08-compile-and-optimization.md#pattern-b-optimize-anything-deferred-phase-4",
    "92-mcp--when-to-use": "06-runtime-and-protocols.md#92-mcp-when-to-use",
    "93-acp--when-to-use": "06-runtime-and-protocols.md#93-acp-when-to-use",
    "52-runtime-agent-resolution": "04-data-flows.md",
    "53-artifact-layout": "04-data-flows.md",
    "54-workflow-diagram-compile": "04-data-flows.md#54-workflow-diagram-compile",
    "54-continuous-improvement-loop": "04-data-flows.md#55-continuous-improvement-loop",
    "55-continuous-improvement-loop": "04-data-flows.md#55-continuous-improvement-loop",
    "6-configuration-architecture": "05-configuration.md#6-configuration-architecture",
    "61-model-registry-merge": "05-configuration.md",
    "62-config-sections": "05-configuration.md#62-config-sections",
    "63-harness-eval-frameworks": "05-configuration.md#63-zaumzeug-eval-frameworks",
    "63-zaumzeug-eval-frameworks": "05-configuration.md#63-zaumzeug-eval-frameworks",
    "64-deploy-eval-gate": "05-configuration.md",
    "65-builtin-tools-catalog": "05-configuration.md",
    "66-phase-1-config-schema": "05-configuration.md",
    "7-model-routing": "05-configuration.md#7-model-routing",
    "8-cli-and-runtime-layering": "06-runtime-and-protocols.md",
    "81-source-roots": "06-runtime-and-protocols.md",
    "82-harness-vs-raw-hayhooks": "06-runtime-and-protocols.md",
    "83-multi-harness-serving": "06-runtime-and-protocols.md",
    "9-client-access-and-protocols": "06-runtime-and-protocols.md",
    "91-protocol-selection": "06-runtime-and-protocols.md",
    "92-mcp--when-to-use": "06-runtime-and-protocols.md#92-mcp-when-to-use",
    "93-acp--when-to-use": "06-runtime-and-protocols.md#93-acp-when-to-use",
    "94-web-deployment-layouts": "06-runtime-and-protocols.md",
    "10-deploy-packager": "07-deploy-packaging.md#10-deploy-packager",
    "101-dev-vs-deploy": "07-deploy-packaging.md",
    "102-packager-steps": "07-deploy-packaging.md#102-packager-steps",
    "103-deploy-manifestjson": "07-deploy-packaging.md#103-deploy-manifestjson",
    "104-git-and-gitignore": "07-deploy-packaging.md#104-git-and-gitignore",
    "105-production-server-dependencies": "07-deploy-packaging.md",
    "106-deploy-platform-targets": "07-deploy-packaging.md",
    "107-target-runtime-install-script": "07-deploy-packaging.md",
    "11-sdk-modules-to-build": "09-sdk-module-map.md",
    "13-debug-and-test-architecture": "10-operations-and-reference.md",
    "131-design-principles": "10-operations-and-reference.md",
    "132-mechanisms": "10-operations-and-reference.md",
    "133-test-pyramid": "10-operations-and-reference.md",
    "135-phase-mapping": "10-operations-and-reference.md#135-phase-mapping",
    "136-testing-playbook": "10-operations-and-reference.md#136-testing-playbook",
    "14-security-phase-1-stance": "10-operations-and-reference.md",
    "15-anti-patterns": "10-operations-and-reference.md",
    "16-supporting-ecosystem-reference": "10-operations-and-reference.md",
}


def arch_base(file_path: Path) -> str:
    if file_path.parent.name == "stories":
        return "../architecture/"
    return "architecture/"


def update_file(file_path: Path) -> bool:
    text = file_path.read_text(encoding="utf-8")
    original = text
    base = arch_base(file_path)

    pattern = re.compile(r"(\.\./)?architecture\.md#([a-z0-9\-_]+)", re.IGNORECASE)

    def repl(m: re.Match[str]) -> str:
        anchor = m.group(2)
        mapped = ANCHOR_TO_FILE.get(anchor)
        if not mapped:
            return m.group(0)
        if "#" in mapped:
            file_name, sub = mapped.split("#", 1)
            return f"{base}{file_name}#{sub}"
        return f"{base}{mapped}#{anchor}"

    text = pattern.sub(repl, text)

    if file_path.name == "prd.md":
        text = text.replace(
            "Technical **how** (stack, flows, protocols, repo layout, SDK modules) lives in **[architecture.md](architecture.md)**.",
            "Technical **how** (stack, flows, protocols, repo layout, SDK modules) lives in **[architecture.md](architecture.md)** and topic files under **[architecture/](architecture/00-README.md)**.",
        )
        text = text.replace(
            "[Architecture §3–8](architecture.md)",
            "[Architecture topics](architecture/00-README.md#architecture-topics)",
        )

    if text != original:
        file_path.write_text(text, encoding="utf-8")
        return True
    return False


def main() -> None:
    targets = [
        p
        for p in DOCS.rglob("*.md")
        if not (p.parent == DOCS / "architecture" and re.match(r"\d{2}-", p.name))
    ]

    count = 0
    for path in sorted(targets):
        if update_file(path):
            print(f"Updated {path.relative_to(ROOT)}")
            count += 1
    print(f"Done — {count} files updated")


if __name__ == "__main__":
    main()

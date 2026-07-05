"""Extract user stories from docs/stories/*-epic.md into docs/stories/epic-stories/."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STORIES = ROOT / "docs" / "stories"
OUT = STORIES / "epic-stories"

EPIC_FILES = [
    "01-epic.md",
    "02-epic.md",
    "03-epic.md",
    "04-epic.md",
    "05-epic.md",
    "06-epic.md",
    "07-epic.md",
    "08-epic.md",
]

STORY_HEADING = re.compile(r"^## (E\d+-S\d+) — (.+)$", re.MULTILINE)


def parse_epic_header(text: str) -> dict[str, str]:
    meta: dict[str, str] = {}
    title_m = re.match(r"^# Epic (E\d+) — (.+)$", text, re.MULTILINE)
    if title_m:
        meta["epic_id"] = title_m.group(1)
        meta["epic_title"] = title_m.group(2).strip()
    phase_m = re.search(r"\| \*\*Phase\*\* \| (\d+) \|", text)
    if phase_m:
        meta["phase"] = phase_m.group(1)
    build_m = re.search(r"\| \*\*Build order\*\* \| \*\*(\d+) of 8\*\*", text)
    if build_m:
        meta["epic_build_order"] = build_m.group(1)
    created_m = re.search(r"\| \*\*Created\*\* \| (\d{4}-\d{2}-\d{2}) \|", text)
    if created_m:
        meta["created"] = created_m.group(1)
    modified_m = re.search(r"\| \*\*Last modified\*\* \| (\d{4}-\d{2}-\d{2}) \|", text)
    if modified_m:
        meta["last_modified"] = modified_m.group(1)
    prd_m = re.search(r"\| \*\*PRD\*\* \| \[(Epic E\d+[^\]]*)\]\(([^)]+)\)", text)
    if prd_m:
        meta["prd_label"] = prd_m.group(1)
        meta["prd_link"] = prd_m.group(2)
    return meta


def extract_stories(epic_text: str) -> list[tuple[str, str, str]]:
    """Return list of (story_id, title, body_including_heading)."""
    matches = list(STORY_HEADING.finditer(epic_text))
    stories: list[tuple[str, str, str]] = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(epic_text)
        story_id = m.group(1)
        title = m.group(2).strip()
        body = epic_text[start:end].rstrip() + "\n"
        stories.append((story_id, title, body))
    return stories


def fix_story_links(body: str, story_to_file: dict[str, str]) -> str:
    """Adjust relative links for files under epic-stories/."""
    body = body.replace("(00-README.md", "(../00-README.md")
    body = re.sub(r"\]\((0\d-epic\.md)", r"](../\1", body)

    # Epic files live one level up; docs/ assets two levels up.
    for prefix in ("architecture/", "prd.md", "ideation-stage.md", "user-docs/", "cloudflare-harness.md"):
        body = body.replace(f"](../{prefix}", f"](../../{prefix}")

    def repl_story_link(label: str, target: str) -> str:
        return f"[{label}]({target})"

    def repl_same_epic_hash(m: re.Match[str]) -> str:
        label = m.group(1)
        anchor = m.group(2)
        if label in story_to_file:
            return repl_story_link(label, f"{story_to_file[label]}{anchor}")
        return m.group(0)

    body = re.sub(
        r"\[(E\d+-S\d+)\]\((#[^)]+)\)",
        repl_same_epic_hash,
        body,
    )

    def repl_epic_hash(m: re.Match[str]) -> str:
        label = m.group(1)
        epic_file = m.group(2)
        anchor = m.group(3)
        if label in story_to_file:
            return repl_story_link(label, f"{story_to_file[label]}{anchor}")
        return repl_story_link(label, f"../{epic_file}{anchor}")

    body = re.sub(
        r"\[(E\d+-S\d+)\]\(\.\./(0\d-epic\.md)(#[^)]+)\)",
        repl_epic_hash,
        body,
    )
    return body


def story_file_header(
    seq: int,
    total: int,
    story_id: str,
    title: str,
    epic_meta: dict[str, str],
    epic_filename: str,
) -> str:
    epic_id = epic_meta.get("epic_id", "?")
    epic_title = epic_meta.get("epic_title", "")
    phase = epic_meta.get("phase", "?")
    epic_build = epic_meta.get("epic_build_order", "?")
    prd_label = epic_meta.get("prd_label", f"Epic {epic_id}")
    prd_link = epic_meta.get("prd_link", "../../prd.md")
    if prd_link.startswith("../") and not prd_link.startswith("../../"):
        prd_link = "../" + prd_link

    return (
        f"# {story_id} — {title}\n\n"
        f"| | |\n"
        f"|---|---|\n"
        f"| **Document** | User story |\n"
        f"| **File** | `docs/stories/epic-stories/{seq:02d}-story.md` |\n"
        f"| **Created** | {epic_meta.get('created', '?')} |\n"
        f"| **Last modified** | {epic_meta.get('last_modified', '?')} |\n"
        f"| **Story ID** | {story_id} |\n"
        f"| **Epic** | [{epic_id} — {epic_title}](../{epic_filename}) |\n"
        f"| **Phase** | {phase} |\n"
        f"| **Epic build order** | {epic_build} of 8 |\n"
        f"| **Story sequence** | {seq} of {total} (global build order) |\n"
        f"| **Source** | Extracted from [`{epic_filename}`](../{epic_filename}) |\n"
        f"| **Related** | [Stories index](../00-README.md) · "
        f"[{prd_label}]({prd_link}) · [Architecture](../../architecture.md) |\n\n"
        f"---\n\n"
    )


def build_index(
    entries: list[dict[str, str | int]],
) -> str:
    lines = [
        "# Epic stories — index\n",
        "| | |",
        "|---|---|",
        "| **Document** | Individual user stories (extracted from epic files) |",
        "| **Folder** | `docs/stories/epic-stories/` |",
        "| **Created** | 2026-07-05 |",
        "| **Last modified** | 2026-07-05 |",
        "| **Related** | [Epic index](../00-README.md) · [PRD](../../prd.md) |",
        "",
        "---",
        "",
        "Stories are numbered in **global build order** (epic file order 01→08, then story order within each epic file).",
        "",
        "| # | Story | Phase | Epic | File |",
        "|---|---|---|---|---|",
    ]
    for e in entries:
        lines.append(
            f"| {e['seq']} | {e['story_id']} — {e['title']} | {e['phase']} | "
            f"[{e['epic_id']}](../{e['epic_file']}) | [{e['seq']:02d}-story.md]({e['seq']:02d}-story.md) |"
        )
    lines.extend(
        [
            "",
            "---",
            "",
            "## Epic source files",
            "",
            "| Build order | Epic file | Epic ID | Phase |",
            "|---|---|---|---|",
            "| 1 | [01-epic.md](../01-epic.md) | E2 | 1 |",
            "| 2 | [02-epic.md](../02-epic.md) | E3 | 1 |",
            "| 3 | [03-epic.md](../03-epic.md) | E1 | 1 |",
            "| 4 | [04-epic.md](../04-epic.md) | E4 | 2 |",
            "| 5 | [05-epic.md](../05-epic.md) | E6 | 2 |",
            "| 6 | [06-epic.md](../06-epic.md) | E5 | 2 |",
            "| 7 | [07-epic.md](../07-epic.md) | E7 | 3 |",
            "| 8 | [08-epic.md](../08-epic.md) | E8 | 4 |",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    OUT.mkdir(exist_ok=True)

    all_stories: list[tuple[str, str, str, dict[str, str], str]] = []
    for epic_filename in EPIC_FILES:
        path = STORIES / epic_filename
        text = path.read_text(encoding="utf-8")
        epic_meta = parse_epic_header(text)
        for story_id, title, body in extract_stories(text):
            all_stories.append((story_id, title, body, epic_meta, epic_filename))

    total = len(all_stories)
    story_to_file: dict[str, str] = {
        story_id: f"{i:02d}-story.md" for i, (story_id, *_rest) in enumerate(all_stories, start=1)
    }

    index_entries: list[dict[str, str | int]] = []
    for seq, (story_id, title, body, epic_meta, epic_filename) in enumerate(all_stories, start=1):
        fixed_body = fix_story_links(body, story_to_file)
        header = story_file_header(seq, total, story_id, title, epic_meta, epic_filename)
        out_path = OUT / f"{seq:02d}-story.md"
        out_path.write_text(header + fixed_body, encoding="utf-8")
        print(f"Wrote {out_path.name} ({story_id})")
        index_entries.append(
            {
                "seq": seq,
                "story_id": story_id,
                "title": title,
                "phase": epic_meta.get("phase", "?"),
                "epic_id": epic_meta.get("epic_id", "?"),
                "epic_file": epic_filename,
            }
        )

    (OUT / "00-README.md").write_text(build_index(index_entries), encoding="utf-8")
    print(f"Wrote 00-README.md ({total} stories)")
    print("Note: run scripts/refine_epic_stories.py after split; then scripts/add_story_implementation_resources.py for library links.")


if __name__ == "__main__":
    main()

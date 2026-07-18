#!/usr/bin/env python3
"""Build compact, source-grounded knowledge notes from an atomic map."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from source_excerpt import select

SECTION = re.compile(r"(?ms)^## (Page|Slide) (\d+)\s*$(.*?)(?=^## (?:Page|Slide) |\Z)")


def source_pages(path: Path) -> tuple[str, dict[int, str]]:
    matches = list(SECTION.finditer(path.read_text(encoding="utf-8")))
    kind = matches[0].group(1) if matches else "Page"
    return kind, {int(match.group(2)): match.group(3).strip() for match in matches}


def compact_unique(items: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        value = re.sub(r"\s+", " ", item).strip()
        key = re.sub(r"[\s*`]+", "", value)
        if value and key not in seen:
            seen.add(key)
            result.append(value)
    return result


def render_blocks(notes: list[str], blocks: list[dict]) -> None:
    for block in blocks:
        notes.extend(["", f"#### {block['title']}", ""])
        items = block.get("items", [])
        if block.get("type") == "steps":
            notes.extend(f"{index}. {line}" for index, line in enumerate(items, 1))
        elif block.get("type") == "formula":
            notes.extend(f"- `{line}`" for line in items)
        else:
            notes.extend(f"- {line}" for line in items)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task_dir")
    parser.add_argument("map_file")
    args = parser.parse_args()
    task = Path(args.task_dir)
    atoms = json.loads(Path(args.map_file).read_text(encoding="utf-8"))["atoms"]
    manifest = json.loads((task / "source_manifest.json").read_text(encoding="utf-8"))
    task_name = manifest.get("task", "课程")
    enrichment_path = task / "knowledge_enrichment.json"
    enrichment = json.loads(enrichment_path.read_text(encoding="utf-8")) if enrichment_path.exists() else {}
    inferred_path = task / "knowledge_inferred.json"
    if inferred_path.exists():
        enrichment.update(json.loads(inferred_path.read_text(encoding="utf-8")))
    cache: dict[str, tuple[str, dict[int, str]]] = {}

    notes = [
        f"# {task_name}期末复习知识点", "",
        "> 内容按“考查要求＋核心内容”组织。标注为补充的内容缺少完整资料支撑，请结合教师口径核对。",
    ]
    rows = [
        "# 原子考点清单", "",
        "| atomic_id | 上级条目 | 原子考点 | 考查动作 | 来源 | 训练题数 |",
        "| --- | --- | --- | --- | --- | ---: |",
    ]
    mindmap = ["mindmap", f"  root(({task_name}期末复习))"]
    current_parent = None

    for atom in atoms:
        source_id = atom["source_id"]
        if source_id not in cache:
            source = task / "sources" / f"{source_id}.md"
            if not source.exists():
                raise FileNotFoundError(f"missing extracted source: {source_id}.md")
            cache[source_id] = source_pages(source)
        section_kind, sections = cache[source_id]
        selected_pages = [sections[page] for page in atom["pages"] if page in sections]
        selected = atom.get("extracts") or select(selected_pages, atom["title"], atom.get("action", ""))
        page_ref = ", ".join(f"{section_kind} {page}" for page in atom["pages"])
        rows.append(
            f"| {atom['id']} | {atom.get('parent', '')} | {atom['title']} | {atom.get('action', '')} | "
            f"{source_id}#{page_ref} | {atom.get('minimum_questions', 3)} |"
        )
        if atom.get("parent") != current_parent:
            current_parent = atom.get("parent")
            notes.extend(["", "---", "", f"## {current_parent}"])
        notes.extend(["", f"### {atom['id']}｜{atom['title']}", "", f"> **考查要求：** {atom.get('action', '')}"])
        custom = enrichment.get(atom["id"])
        if custom:
            render_blocks(notes, custom.get("blocks", []))
            notes.extend(["", f"> **补充说明：** {custom.get('note', '部分内容由模型知识补全，请结合教师口径核对。')}"])
        else:
            notes.extend(["", "#### 核心内容", ""])
            notes.extend(f"- {text}" for text in compact_unique(selected))

    parents: dict[str, list[dict]] = {}
    for atom in atoms:
        parents.setdefault(atom.get("parent", "未分组"), []).append(atom)
    for parent, children in parents.items():
        mindmap.append(f"    {parent}")
        for child in children:
            safe = child["title"].replace("(", "（").replace(")", "）").replace(":", "：")
            mindmap.append(f"      {child['id']} {safe}")

    (task / "思维导图.mmd").write_text("\n".join(mindmap) + "\n", encoding="utf-8")
    (task / "atomic_points.md").write_text("\n".join(rows) + "\n", encoding="utf-8")
    (task / "知识点.md").write_text("\n".join(notes).rstrip() + "\n", encoding="utf-8")
    (task / "思维导图.md").write_text(
        f"# {task_name}期末复习思维导图\n\n![{task_name}期末复习思维导图](思维导图.png)\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Build source-faithful knowledge notes from an atomic-point JSON map.

The script copies selected extracted-source page blocks verbatim.  It never
summarizes source text, so the resulting notes can replace slide browsing.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from source_excerpt import select

PAGE = re.compile(r"(?ms)^## Page (\d+)\s*$(.*?)(?=^## Page |\Z)")
LABELS = (
    "定义", "目标", "作用", "核心思想", "核心作用", "分类区别", "区别",
    "公式", "值域", "参数", "步骤", "流程", "优点", "缺点", "应用",
    "处理方式", "判断标准", "关键参数", "基本思想",
)


def source_pages(path: Path) -> dict[int, str]:
    return {int(m.group(1)): m.group(2).strip() for m in PAGE.finditer(path.read_text(encoding="utf-8"))}


def table_row(text: str, title: str, action: str) -> tuple[str, str]:
    label = "核心内容"
    content = text.strip()
    matched = re.match(r"^([^：:]{1,16})[：:]\s*(.+)$", content)
    if matched and any(key in matched.group(1) for key in LABELS):
        label, content = matched.group(1).strip(), matched.group(2).strip()
    else:
        for key in LABELS:
            if key in content:
                label = key
                break
    terms = set(re.findall(r"[A-Z][A-Za-z-]{1,}|[\u4e00-\u9fff]{2,8}", title))
    terms.update(word for word in re.split(r"[、，,/与及\s]+", action) if 2 <= len(word) <= 8)
    terms = {
        term for term in terms
        if term and term not in {"基本概念", "核心思想", "实现流程", "应用场景"}
    }
    if terms:
        pattern = re.compile("|".join(re.escape(term) for term in sorted(terms, key=len, reverse=True)))
        content = pattern.sub(lambda match: f"**{match.group(0)}**", content)
    content = content.replace("|", r"\|").replace("\n", "<br>")
    return label, content


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task_dir")
    parser.add_argument("map_file", help="JSON: {atoms:[{id,title,source_id,pages:[...]}]}")
    args = parser.parse_args()
    task = Path(args.task_dir)
    atoms = json.loads(Path(args.map_file).read_text(encoding="utf-8"))["atoms"]
    cache: dict[str, dict[int, str]] = {}
    notes = [
        "# 数据挖掘期末复习知识点", "",
        "> 使用说明：每个原子考点只保留能够直接回答该考点的来源内容；背景故事、重复页面和无关延伸已删除。",
    ]
    mindmap = ["# 思维导图", "", "```mermaid", "mindmap", "  root((数据挖掘期末复习))"]
    rows = [
        "# 原子考点清单", "",
        "| atomic_id | 上级条目 | 原子考点 | 考查动作 | 来源 | 训练题数 |",
        "| --- | --- | --- | --- | --- | ---: |",
    ]
    current_parent = None
    for index, atom in enumerate(atoms, 1):
        source_id = atom["source_id"]
        if source_id not in cache:
            source = next((task / "sources").glob(f"{source_id}.md"), None)
            if source is None:
                raise FileNotFoundError(f"missing extracted source: {source_id}.md")
            cache[source_id] = source_pages(source)
        selected_pages = [cache[source_id][page] for page in atom["pages"]]
        selected = atom.get("extracts") or select(
            selected_pages, atom["title"], atom.get("action", "")
        )
        page_ref = ", ".join(f"Page {page}" for page in atom["pages"])
        rows.append(
            f"| {atom['id']} | {atom.get('parent', '')} | {atom['title']} | "
            f"{atom.get('action', '')} | {source_id}#{page_ref} | {atom.get('minimum_questions', 3)} |"
        )
        if atom.get("parent") != current_parent:
            current_parent = atom.get("parent")
            notes.extend(["", "---", "", f"## {current_parent}"])
        procedural = any(
            key in (atom.get("action", "") + atom["title"])
            for key in ("步骤", "流程", "计算过程", "实现过程")
        )
        notes.extend([
            "", f"### {atom['id']}｜{index}. {atom['title']}", "",
            f"| 考点编号 | 考查要求 | 来源 |",
            f"| --- | --- | --- |",
            f"| `{atom['id']}` | {atom.get('action', '')} | `{source_id} · {page_ref}` |",
            "", "#### 步骤与计算" if procedural else "#### 必背内容", "",
        ])
        if procedural:
            for step, text in enumerate(selected, 1):
                notes.append(f"{step}. {text}")
        else:
            notes.extend(["| 要点 | 内容 |", "| --- | --- |"])
            for text in selected:
                label, content = table_row(text, atom["title"], atom.get("action", ""))
                notes.append(f"| **{label}** | {content} |")
    parents: dict[str, list[dict]] = {}
    for atom in atoms:
        parents.setdefault(atom.get("parent", "未分组"), []).append(atom)
    for parent, children in parents.items():
        mindmap.append(f"    {parent}")
        for child in children:
            safe_title = child["title"].replace("(", "（").replace(")", "）").replace(":", "：")
            mindmap.append(f"      {child['id']} {safe_title}")
    mindmap.append("```")
    (task / "atomic_points.md").write_text("\n".join(rows) + "\n", encoding="utf-8")
    (task / "知识点.md").write_text("\n".join(notes).rstrip() + "\n", encoding="utf-8")
    (task / "思维导图.md").write_text("\n".join(mindmap) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

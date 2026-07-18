#!/usr/bin/env python3
"""Extract only PDF pages relevant to an established atomic-point map."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def terms_from_map(path: Path) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    terms: list[str] = []
    for atom in data.get("atoms", []):
        for value in (atom.get("title", ""), atom.get("parent", ""), atom.get("action", "")):
            terms.extend(re.findall(r"[A-Za-z][A-Za-z0-9_.-]{2,}|[\u4e00-\u9fff]{2,12}", value))
    return list(dict.fromkeys(term.lower() for term in terms if len(term) >= 2))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf")
    parser.add_argument("atomic_map")
    parser.add_argument("output")
    parser.add_argument("--max-pages", type=int, default=40)
    parser.add_argument("--context", type=int, default=0, choices=(0, 1))
    args = parser.parse_args()
    from pypdf import PdfReader

    pdf = Path(args.pdf).resolve()
    output = Path(args.output).resolve()
    terms = terms_from_map(Path(args.atomic_map))
    reader = PdfReader(str(pdf))
    pages: list[tuple[int, int, str, list[str]]] = []
    for number, page in enumerate(reader.pages, 1):
        text = (page.extract_text() or "").encode("utf-8", errors="replace").decode("utf-8")
        lowered = text.lower()
        hits = [term for term in terms if term in lowered]
        if hits:
            score = sum(lowered.count(term) for term in hits) + len(hits) * 2
            pages.append((score, number, text, hits))
    selected = {number for _, number, _, _ in sorted(pages, reverse=True)[: args.max_pages]}
    if args.context:
        selected |= {n + d for n in selected for d in (-1, 1) if 1 <= n + d <= len(reader.pages)}
    selected = set(sorted(selected)[: args.max_pages])
    lookup = {number: (text, hits) for _, number, text, hits in pages}
    blocks = ["# 考点定向抽取", "", f"> 原文件：{pdf.name}；总页数：{len(reader.pages)}；仅保留与既定原子考点命中的 {len(selected)} 页。"]
    for number in sorted(selected):
        text, hits = lookup.get(number, (reader.pages[number - 1].extract_text() or "", []))
        blocks.extend(["", f"## Page {number}", "", f"命中词：{', '.join(hits)}", "", text.strip()])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(blocks).rstrip() + "\n", encoding="utf-8")
    print(json.dumps({"pdf_pages": len(reader.pages), "selected_pages": len(selected), "output": str(output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

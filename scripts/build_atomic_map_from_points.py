#!/usr/bin/env python3
"""Build atomic_map.json from the canonical atomic_points.md table."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def pages_from(value: str) -> list[int]:
    page_text = value.split("#Page", 1)[1]
    pages: list[int] = []
    for part in page_text.split(","):
        part = part.strip()
        if "-" in part:
            start, end = map(int, part.split("-", 1))
            pages.extend(range(start, end + 1))
        elif part:
            pages.append(int(part))
    return sorted(set(pages))


def main() -> int:
    task = Path(sys.argv[1])
    rows = []
    parents = []
    pattern = re.compile(r"^\| (AP-\d{3}) \| ([^|]+) \| ([^|]+) \| ([^|]+) \| (SRC-\d{3}#Page [^|]+) \|")
    for line in (task / "atomic_points.md").read_text(encoding="utf-8").splitlines():
        match = pattern.match(line)
        if not match:
            continue
        atomic_id, parent, title, action, source = [item.strip() for item in match.groups()]
        source_id = source.split("#", 1)[0]
        rows.append({"id": atomic_id, "parent": parent, "title": title, "action": action,
                     "source_id": source_id, "pages": pages_from(source)})
        if parent not in parents:
            parents.append(parent)
    output = {"version": 1, "outline_parents": parents, "atoms": rows}
    (task / "atomic_map.json").write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"atoms": len(rows), "parents": len(parents)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

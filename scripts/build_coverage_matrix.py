#!/usr/bin/env python3
"""Build a compact coverage matrix from stable IDs and source references."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

POINT = re.compile(r"^#{3,6}\s+([A-Z]+(?:-[A-Za-z0-9_-]+|\d+))\s+(.+?)$", re.M)
SOURCE = re.compile(r"SRC-\d{3}(?:#(?:Page\s+)?\d+(?:-\d+)?)?")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task_dir")
    args = parser.parse_args()
    task_dir = Path(args.task_dir).resolve()
    try:
        lock = json.loads((task_dir / "review_lock.yaml").read_text(encoding="utf-8"))
        outputs = lock["outputs"]
        row_map: dict[str, dict[str, object]] = {}
        for filename in outputs:
            text = (task_dir / filename).read_text(encoding="utf-8")
            points = list(POINT.finditer(text))
            for index, match in enumerate(points):
                end = points[index + 1].start() if index + 1 < len(points) else len(text)
                block = text[match.end():end]
                point_id = match.group(1)
                row = row_map.setdefault(point_id, {
                    "point_id": point_id,
                    "title": match.group(2),
                    "file": [],
                    "question_count": 0,
                    "sources": set(),
                })
                row["file"].append(filename)
                row["sources"].update(SOURCE.findall(block))
        question_manifest = json.loads((task_dir / "question_manifest.json").read_text(encoding="utf-8"))
        counts: dict[str, int] = {}
        for item in question_manifest.get("questions", []):
            atomic_id = item.get("atomic_id")
            if atomic_id:
                counts[atomic_id] = counts.get(atomic_id, 0) + 1
        for point_id, row in row_map.items():
            row["question_count"] = counts.get(point_id, 0)
        rows = [{
            "point_id": row["point_id"], "title": row["title"],
            "file": ";".join(row["file"]), "question_count": row["question_count"],
            "sources": ";".join(sorted(row["sources"])),
        } for row in row_map.values()]
        output = task_dir / "coverage_matrix.csv"
        with output.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["point_id", "title", "file", "question_count", "sources"])
            writer.writeheader()
            writer.writerows(rows)
    except (OSError, KeyError, json.JSONDecodeError) as exc:
        print(f"[coverage] ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"output": str(output), "rows": len(rows)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

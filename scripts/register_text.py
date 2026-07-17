#!/usr/bin/env python3
"""Register user-provided conversational text as a first-class task source."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


def safe_slug(value: str) -> str:
    slug = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", value.strip(), flags=re.UNICODE).strip("-")
    return slug[:80] or "user-text"


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task_dir")
    parser.add_argument("--title", required=True, help="用户输入的简短来源标题")
    parser.add_argument("--input", required=True, help="保存原始对话文本的 UTF-8 Markdown/文本文件")
    parser.add_argument("--role", choices=("primary", "supporting"), default="primary")
    parser.add_argument("--course-match", default="user_declared")
    parser.add_argument("--delete-input", action="store_true", help="登记完成后删除临时输入文件")
    args = parser.parse_args()

    try:
        task_dir = Path(args.task_dir).resolve()
        incoming = Path(args.input).resolve()
        if not task_dir.is_dir() or not incoming.is_file():
            raise ValueError("任务目录或文本输入文件不存在")
        manifest_path = task_dir / "source_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        text = incoming.read_text(encoding="utf-8")
        if not text.strip():
            raise ValueError("用户文本不能为空")
        text_hash = digest(text)
        for item in manifest.get("sources", []):
            if item.get("sha256") == text_hash:
                print(json.dumps({"registered": False, "reason": "duplicate", "source": item}, ensure_ascii=False))
                return 0
        source_id = f"SRC-{len(manifest.get('sources', [])) + 1:03d}"
        target = task_dir / "sources" / f"{source_id}-{safe_slug(args.title)}.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        record = {
            "source_id": source_id,
            "original_name": args.title,
            "stored_path": target.relative_to(task_dir).as_posix(),
            "normalized_path": target.relative_to(task_dir).as_posix(),
            "sha256": text_hash,
            "status": "parsed",
            "kind": "user_text",
            "role": args.role,
            "course_match": args.course_match,
            "imported_at": datetime.now(timezone.utc).isoformat(),
            "error": None,
        }
        manifest.setdefault("sources", []).append(record)
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if args.delete_input:
            incoming.unlink()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"[register-text] ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"registered": True, "source": record}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

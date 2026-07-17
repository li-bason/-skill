#!/usr/bin/env python3
"""Update the single session summary and the mandatory progress log."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
SESSIONS = SKILL_ROOT / "sessions"


def safe_key(value: str) -> str:
    value = value.strip()
    if not value or any(ch in value for ch in '<>:"/\\|?*\0'):
        raise ValueError("session 标识非法")
    return value


def update(task_dir: Path, stage: str, next_step: str, session_key: str | None) -> tuple[Path, Path]:
    task_dir = task_dir.resolve()
    task_dir.relative_to(SKILL_ROOT.resolve())
    lock = json.loads((task_dir / "review_lock.yaml").read_text(encoding="utf-8"))
    name = lock["task"]["name"]
    relative = task_dir.relative_to(SKILL_ROOT).as_posix()
    key = safe_key(session_key or name)
    SESSIONS.mkdir(parents=True, exist_ok=True)
    session = SESSIONS / f"{key}.md"
    now = datetime.now().astimezone().isoformat(timespec="minutes")
    artifacts = [
        p.name for p in sorted(task_dir.iterdir())
        if p.is_file() and p.name not in {"progress-log.md"}
    ]
    lines = "\n".join(f"- `{relative}/{item}`" for item in artifacts) or "- 暂无"
    session.write_text(
        f"# {name} 会话摘要\n\n- 任务：`{relative}`\n- 阶段：{stage}\n- 更新时间：{now}\n\n"
        f"## 当前文件\n{lines}\n\n## 下一步\n- {next_step}\n",
        encoding="utf-8",
    )
    progress = task_dir / "progress-log.md"
    old = progress.read_text(encoding="utf-8") if progress.exists() else "# Progress Log\n"
    old = re.sub(r"\n## Current Status.*\Z", "", old, flags=re.S).rstrip()
    old += (
        f"\n\n## Current Status\n- 更新时间：{now}\n- 当前阶段：{stage}\n"
        f"- Session：`{session.relative_to(SKILL_ROOT).as_posix()}`\n- 下一步：{next_step}\n"
    )
    progress.write_text(old + "\n", encoding="utf-8")
    return session, progress


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task_dir")
    parser.add_argument("--stage", default="进行中")
    parser.add_argument("--next", dest="next_step", default="继续当前任务")
    parser.add_argument("--session-key")
    args = parser.parse_args()
    try:
        session, progress = update(Path(args.task_dir), args.stage, args.next_step, args.session_key)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"[update-session] ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"session": str(session), "progress": str(progress)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

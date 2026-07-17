#!/usr/bin/env python3
"""Create or inspect stable final-exam-prep task directories."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
TASKS_ROOT = SKILL_ROOT / "tasks"

FINAL_OUTPUTS = {
    "liberal-arts": ["atomic_points.md", "知识点.md", "思维导图.md", "题目.md", "答案.md"],
    "science": ["atomic_points.md", "知识点.md", "思维导图.md", "题目.md", "答案.md"],
    "engineering": ["atomic_points.md", "知识点.md", "思维导图.md", "题目.md", "答案.md"],
    "language": ["复习总结.md", "思维导图.md"],
}
TEMPLATES = {
    "liberal-arts": ("final-three-files-v1", "liberal-arts-v1", "liberal-arts-answer-v1"),
    "science": ("final-three-files-v1", "science-v1", "calculation-answer-v1"),
    "engineering": ("final-three-files-v1", "engineering-v1", "calculation-answer-v1"),
    "language": ("language-summary-v1", "language-v1", "language-practice-v1"),
    "contest-general": ("contest-gap-training-v1", "contest-general-v1", "contest-gap-question-v1"),
}


def safe_name(value: str) -> str:
    value = value.strip()
    if not value or value in {".", ".."}:
        raise ValueError("名称不能为空")
    if any(ch in value for ch in '<>:"/\\|?*\0') or ".." in Path(value).parts:
        raise ValueError("名称包含非法字符或路径穿越")
    return value


def write_missing(path: Path, text: str) -> bool:
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


def build_lock(mode: str, name: str, category: str, task_dir: Path, outputs: list[str]) -> dict:
    review_frame, subject_preset, question_pattern = TEMPLATES[category]
    return {
        "version": 1,
        "task": {
            "mode": "final_exam" if mode == "final" else "contest",
            "name": name,
            "category": category,
            "task_dir": task_dir.relative_to(SKILL_ROOT).as_posix(),
        },
        "templates": {
            "review_frame": review_frame,
            "subject_preset": subject_preset,
            "question_pattern": question_pattern,
        },
        "inputs": {
            "manifest": "source_manifest.json",
            "outline_required": mode == "final",
            "question_types_required": mode == "final" and category != "language",
        },
        "outputs": outputs,
        "rules": {
            "full_pipeline_required": True,
            "minimum_questions_per_point": 3,
            "difficulty_ratio": {"basic": 0.4, "medium": 0.4, "advanced": 0.2},
            "stable_ids": True,
            "source_attribution": True,
            "update_mode": "incremental_with_reorganize",
        },
        "status": "draft_pending_user_confirmation",
    }


def initialize(mode: str, name: str, category: str | None, directory: str | None = None) -> dict:
    name = safe_name(name)
    custom_dir = Path(directory).resolve() if directory else None
    if custom_dir:
        try:
            custom_dir.relative_to(SKILL_ROOT.resolve())
        except ValueError as exc:
            raise ValueError("--directory 必须位于 final-exam-prep skill 根目录内") from exc
    if mode == "final":
        if category not in FINAL_OUTPUTS:
            raise ValueError(f"分类必须是：{', '.join(FINAL_OUTPUTS)}")
        outputs = FINAL_OUTPUTS[category]
        task_dir = custom_dir or TASKS_ROOT / "期末" / name
        actual_category = category
    else:
        outputs = ["提纲.md", "思维导图.md", "新题答案.md"]
        task_dir = custom_dir or TASKS_ROOT / "竞赛" / name
        actual_category = "contest-general"

    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "sources").mkdir(exist_ok=True)
    created: list[str] = []
    spec = f"""# {name} Review Spec

## Task Information
- 任务类型：{"期末" if mode == "final" else "竞赛"}
- 名称：{name}
- 分类：{actual_category}
- 状态：待归集材料与用户确认

## Scope & Inputs
- 待填写

## Template Selection
- 待填写

## Output Plan
- {chr(10).join(outputs)}

## Question Strategy
- 难度比例：基础 40% / 中等 40% / 综合 20%

## Source & Update Policy
- 所有材料登记到 source_manifest.json
- 正式内容必须使用来源状态
"""
    if write_missing(task_dir / "review_spec.md", spec):
        created.append("review_spec.md")
    lock = build_lock(mode, name, actual_category, task_dir, outputs)
    if write_missing(task_dir / "review_lock.yaml", json.dumps(lock, ensure_ascii=False, indent=2) + "\n"):
        created.append("review_lock.yaml")
    manifest = {"version": 1, "task": name, "sources": [], "conflicts": []}
    if write_missing(task_dir / "source_manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"):
        created.append("source_manifest.json")
    now = datetime.now(timezone.utc).astimezone().isoformat(timespec="minutes")
    progress = f"# Progress Log\n\n- 更新时间：{now}\n- 当前阶段：任务已初始化\n- 下一步：导入材料并完善 review_spec.md\n"
    if write_missing(task_dir / "progress-log.md", progress):
        created.append("progress-log.md")
    for filename in outputs:
        if write_missing(task_dir / filename, f"# {Path(filename).stem}\n"):
            created.append(filename)
    return {"task_dir": str(task_dir), "created": created}


def status(path: str) -> dict:
    task_dir = Path(path).resolve()
    if not task_dir.is_dir():
        raise ValueError(f"任务目录不存在：{task_dir}")
    task_dir.relative_to(SKILL_ROOT.resolve())
    return {"task_dir": str(task_dir), "files": sorted(p.name for p in task_dir.iterdir())}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    final = sub.add_parser("init-final")
    final.add_argument("name")
    final.add_argument("--category", choices=sorted(FINAL_OUTPUTS), required=True)
    final.add_argument("--directory", help="直接创建到指定任务目录（必须位于 skill 根目录内）")
    contest = sub.add_parser("init-contest")
    contest.add_argument("name")
    contest.add_argument("--directory", help="直接创建到指定任务目录（必须位于 skill 根目录内）")
    show = sub.add_parser("status")
    show.add_argument("path")
    args = parser.parse_args()
    try:
        if args.command == "init-final":
            result = initialize("final", args.name, args.category, args.directory)
        elif args.command == "init-contest":
            result = initialize("contest", args.name, None, args.directory)
        else:
            result = status(args.path)
    except (OSError, ValueError) as exc:
        print(f"[task-manager] ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

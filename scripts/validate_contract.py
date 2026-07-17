#!/usr/bin/env python3
"""Validate review_lock contract files stored in JSON-compatible format."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent


def validate(path: Path) -> dict:
    errors: list[str] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"valid": False, "errors": [f"合同无法解析：{exc}"]}
    for key in ("version", "task", "templates", "inputs", "outputs", "rules"):
        if key not in data:
            errors.append(f"缺少字段：{key}")
    task = data.get("task", {})
    if task.get("mode") not in {"final_exam", "contest"}:
        errors.append("task.mode 必须是 final_exam 或 contest")
    if task.get("category") not in {
        "liberal-arts", "science", "engineering", "language", "contest-general"
    }:
        errors.append("task.category 非法")
    if not isinstance(data.get("outputs"), list) or not data.get("outputs"):
        errors.append("outputs 必须是非空列表")
    rules = data.get("rules", {})
    if rules.get("full_pipeline_required") is not True:
        errors.append("rules.full_pipeline_required 必须为 true；触发 skill 后必须执行完整流程")
    if not isinstance(rules.get("minimum_questions_per_point"), int):
        errors.append("rules.minimum_questions_per_point 必须是整数")
    ratio = rules.get("difficulty_ratio", {})
    if set(ratio) != {"basic", "medium", "advanced"} or abs(sum(ratio.values()) - 1) > 1e-6:
        errors.append("difficulty_ratio 必须包含 basic/medium/advanced 且合计为 1")
    try:
        index = json.loads((SKILL_ROOT / "templates" / "index.json").read_text(encoding="utf-8"))
        known = set().union(*(section.keys() for section in index.values() if isinstance(section, dict)))
        for field, value in data.get("templates", {}).items():
            if value not in known:
                errors.append(f"模板不存在：{field}={value}")
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"模板索引无法读取：{exc}")
    return {"valid": not errors, "errors": errors, "contract": data}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("contract")
    args = parser.parse_args()
    report = validate(Path(args.contract))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

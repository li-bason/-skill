#!/usr/bin/env python3
"""Validate the reusable Markdown structure contract for every workflow."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ANSWER_HEADING = re.compile(
    r"(?m)^####\s+([A-Za-z0-9_-]+)｜(?:选择题|判断题|填空题|简答题|计算题|方案设计题|答案)$"
)
QUESTION_HEADING = re.compile(
    r"(?m)^####\s+([A-Za-z0-9_-]+)｜(?:选择题|判断题|填空题|简答题|计算题|方案设计题)$"
)
BAD_CONTENT = re.compile(
    r"\?{2,}|\?[A-Za-z0-9]|[\u200b-\u200d]|[�]|"
    r"输入0|输出0|-0\.5\s+-0\.5|数据预处理章节|Ø|NO!|分类任务训练数据"
)
SKELETON = re.compile(
    r"完整说明.+定义、核心内容和作用|围绕.+逐项完成以下考查要求|"
    r"结合一个数据挖掘场景，说明如何运用"
)
PACKED_POINTS = re.compile(
    r"(?m)^.*(?:①[^\n]*②|第一[^\n]*第二[^\n]*第三|步骤一[^\n]*步骤二|"
    r"(?:•[^\n]*){2,}|(?:➢[^\n]*){2,}).*$"
)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def validate_choice_layout(text: str, errors: list[str], label: str) -> int:
    count = len(re.findall(r"【选择】", text))
    if not count:
        return 0
    for option in "ABCD":
        actual = len(re.findall(rf"(?m)^{option}：.+$", text))
        if actual != count:
            errors.append(f"{label}：{count} 道选择题，但有 {actual} 个 {option} 选项")
    preview = len(
        re.findall(
            r"(?ms)【选择】[^\n]+\n\nA：.+?\n\nB：.+?\n\nC：.+?\n\nD：.+?(?:\n\n|$)",
            text,
        )
    )
    if preview != count:
        errors.append(f"{label}：仅 {preview}/{count} 道选择题能在 Markdown 预览中正确分段")
    return count


def validate(task_dir: Path) -> dict:
    task_dir = task_dir.resolve()
    errors: list[str] = []
    try:
        lock = json.loads((task_dir / "review_lock.yaml").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"valid": False, "errors": [f"review_lock.yaml 无法解析：{exc}"]}

    outputs = lock.get("outputs", [])
    combined = "\n".join(read(task_dir / name) for name in outputs)
    if BAD_CONTENT.search(combined):
        errors.append("正式产物包含公式乱码、图表标签或幻灯片残留")
    if SKELETON.search(combined):
        errors.append("正式产物包含未加工的通用题目骨架")
    packed = PACKED_POINTS.search(combined)
    if packed:
        errors.append(f"正式产物把多个要点或步骤挤在同一行：{packed.group(0)[:100]}")

    mode = lock.get("task", {}).get("mode")
    category = lock.get("task", {}).get("category")
    question_name = "新题答案.md" if mode == "contest" else "题目.md"
    answer_name = "新题答案.md" if mode == "contest" else "答案.md"
    question_text = read(task_dir / question_name)
    answer_text = read(task_dir / answer_name)
    choices = validate_choice_layout(question_text, errors, question_name)

    try:
        question_manifest = json.loads((task_dir / "question_manifest.json").read_text(encoding="utf-8"))
        q_ids = [item.get("question_id") for item in question_manifest.get("questions", [])]
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"question_manifest.json 无法解析：{exc}")
        q_ids = []
    visible_q_ids = QUESTION_HEADING.findall(question_text)
    a_ids = ANSWER_HEADING.findall(answer_text)
    if visible_q_ids != q_ids:
        errors.append("题目可见 ID 与 question_manifest.json 不一致")
    if q_ids != a_ids:
        errors.append("题目与答案 ID 或顺序不一致")
    if re.search(r"(?m)^[123]\.\s+\*\*(?:答案|结论|参考答案|计算过程)", answer_text):
        errors.append("答案仍使用循环的 1、2、3 编号")

    atoms = re.findall(r"(?m)^\|\s*(AP-[A-Za-z0-9_-]+)\s*\|", read(task_dir / "atomic_points.md"))
    if mode == "final_exam" and category not in {"language", None}:
        knowledge = read(task_dir / "知识点.md")
        for atomic_id in atoms:
            match = re.search(rf"(?m)^###\s+{re.escape(atomic_id)}\b.*$", knowledge)
            if not match:
                errors.append(f"知识点缺少 {atomic_id}")
                continue
            later = re.search(r"(?m)^###\s+", knowledge[match.end():])
            end = match.end() + later.start() if later else len(knowledge)
            block = knowledge[match.end():end]
            has_requirement = "> **考查要求：**" in block
            has_content = bool(re.search(r"(?m)^####\s+.+$", block)) and bool(
                re.search(r"(?m)^(?:- |\d+\. )", block)
            )
            if not (has_requirement and has_content):
                errors.append(f"{atomic_id} 未使用‘考查要求＋分块内容’结构")

    if category == "language":
        summary = read(task_dir / "复习总结.md")
        for heading in ("词汇语法", "阅读", "翻译", "写作"):
            if not re.search(rf"(?m)^##\s+{heading}\b", summary):
                errors.append(f"语言总结缺少 {heading}")

    return {
        "valid": not errors,
        "errors": errors,
        "metrics": {
            "questions": len(q_ids),
            "answers": len(a_ids),
            "choices": choices,
            "atoms": len(atoms),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task_dir")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = validate(Path(args.task_dir))
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else ("PASS" if report["valid"] else "\n".join(report["errors"])))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

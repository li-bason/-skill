#!/usr/bin/env python3
"""Regression-test the golden demo and reusable template contracts."""

from __future__ import annotations

import sys
import base64
from pathlib import Path

from validate_output_structure import validate

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    errors: list[str] = []
    demo = ROOT / "demo" / "数据挖掘"
    if demo.is_dir():
        mindmap_png = demo / "思维导图.png"
        temporary_png = not mindmap_png.exists()
        if temporary_png:
            mindmap_png.write_bytes(base64.b64decode(
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
            ))
        try:
            report = validate(demo)
        finally:
            if temporary_png:
                mindmap_png.unlink(missing_ok=True)
        errors.extend(report["errors"])
        expected = {"questions": 207, "answers": 207, "choices": 69, "atoms": 69}
        for key, value in expected.items():
            if report["metrics"].get(key) != value:
                errors.append(f"黄金 demo {key}={report['metrics'].get(key)}，期望 {value}")

    required_fragments = {
        "templates/review-frames/final-three-files.md": [
            "> **考查要求：**", "#### 逐步推导", "#### Q-...｜选择题",
        ],
        "templates/question-patterns/calculation-answer.md": ["#### Q-...｜计算题"],
        "templates/question-patterns/liberal-arts-answer.md": ["#### Q-...｜简答题"],
        "templates/question-patterns/language-accumulation.md": ["是否将这个词条加入词汇语法积累表", "英文句子", "最长有效词组优先"],
        "templates/question-patterns/contest-gap-question.md": ["#### CQ-...｜题目", "#### CQ-...｜答案"],
    }
    for relative, fragments in required_fragments.items():
        path = ROOT / relative
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        for fragment in fragments:
            if fragment not in text:
                errors.append(f"{relative} 缺少结构片段：{fragment}")

    for error in errors:
        print(f"ERROR: {error}")
    print("PASS" if not errors else "FAIL")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

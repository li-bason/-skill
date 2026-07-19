#!/usr/bin/env python3
"""Regression checks shared by liberal-arts, science, engineering, language, and contest routes."""

from __future__ import annotations

import sys
from pathlib import Path

from validate_review import BROKEN_MATH, EXAM_TYPE_LEAK, QUESTION_OUTLINE_LEAK
from validate_output_structure import PACKED_POINTS

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    errors: list[str] = []
    required = {
        "SKILL.md": ["原子点标题 → 考查要求 → 分块内容", "所有板块统一执行逐点排版", "文科、理科、工科共享同一内容契约", "inferred", "章节标题、题型目录", "临时目录不得预先创建"],
        "workflows/final-exam.md": ["原子点标题 → 考查要求 → 分块内容", "文科补充背景", "语言类补充语法规则"],
        "workflows/contest-review.md": ["大量资料缺失时不逐站联网", "不得把题型目录"],
        "templates/subject-presets/liberal-arts.md": ["概念/背景/原因/内容/影响/评价/论据分块", "标记 `inferred`"],
        "templates/subject-presets/language.md": ["大量缺失时直接用模型知识", "标记 `inferred`"],
        "templates/review-frames/language-summary.md": ["可执行规则", "禁止用空表格", "标记 `inferred`"],
        "templates/review-frames/final-three-files.md": ["文科、理科、工科共用本骨架", "所有学科均采用逐点排版", "长推导逐步换行"],
        "workflows/template-selection.md": ["文科、理科、工科使用同一个", "目录过滤、去重、来源隔离"],
    }
    forbidden = {
        "workflows/final-exam.md": ["考点信息表", "概念型最终显示为 `要点 | 内容` 表格"],
        "templates/subject-presets/language.md": ["板块资料不足：少量联网补足板块总结"],
        "templates/review-frames/language-summary.md": ["| 要点 | 内容 | 来源 |"],
    }
    for relative, fragments in required.items():
        text = (ROOT / relative).read_text(encoding="utf-8")
        for fragment in fragments:
            if fragment not in text:
                errors.append(f"{relative} 缺少跨路由规则：{fragment}")
    for relative, fragments in forbidden.items():
        text = (ROOT / relative).read_text(encoding="utf-8")
        for fragment in fragments:
            if fragment in text:
                errors.append(f"{relative} 仍包含旧规则：{fragment}")

    leak_samples = [
        "第一章 导论 •选择、填空、判断题 •知识点",
        "关于该观点，下列哪一项符合课程材料？",
        "以下内容与本考点无关：文艺复兴的影响",
    ]
    for sample in leak_samples:
        if not (EXAM_TYPE_LEAK.search(sample) or QUESTION_OUTLINE_LEAK.search(sample)):
            errors.append(f"目录/拼接题泄漏未被拦截：{sample}")
    for sample in ("pq", "含有\ue123私用字符", "公式??"):
        if not BROKEN_MATH.search(sample):
            errors.append(f"乱码未被拦截：{sample!r}")
    for sample in ("①背景 ②原因 ③影响", "第一步分析第二步计算第三步检查", "•规则一 •规则二"):
        if not PACKED_POINTS.search(sample):
            errors.append(f"同一行堆叠要点未被拦截：{sample}")
    from gate import SKIP_PARTS
    for directory in ("tmp", "tmp_pdf_check"):
        if directory not in SKIP_PARTS:
            errors.append(f"打包器未排除临时目录：{directory}")

    for error in errors:
        print(f"ERROR: {error}")
    print("PASS" if not errors else "FAIL")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

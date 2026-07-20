#!/usr/bin/env python3
"""Regression checks shared by liberal-arts, science, engineering, language, and contest routes."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from validate_review import BROKEN_MATH, EXAM_TYPE_LEAK, QUESTION_OUTLINE_LEAK
from validate_review import validate as validate_review
from validate_output_structure import PACKED_POINTS
from validate_output_structure import validate as validate_output_structure

ROOT = Path(__file__).resolve().parent.parent


def check_language_accumulation(errors: list[str]) -> None:
    """Prove that a language task can ship with accumulation tables only."""
    with tempfile.TemporaryDirectory(prefix="fep-language-") as directory:
        task = Path(directory)
        outputs = ["词汇语法积累表.md", "翻译积累表.md", "写作积累表.md"]
        lock = {
            "version": 1,
            "task": {"mode": "final_exam", "name": "语言积累测试", "category": "language"},
            "templates": {
                "review_frame": "language-summary-v1",
                "subject_preset": "language-v1",
                "question_pattern": "language-accumulation-v1",
            },
            "inputs": {"manifest": "source_manifest.json", "outline_required": False, "question_types_required": False},
            "outputs": outputs,
            "rules": {
                "full_pipeline_required": True,
                "minimum_questions_per_point": 0,
                "difficulty_ratio": {"basic": 0.4, "medium": 0.4, "advanced": 0.2},
                "stable_ids": True,
                "source_attribution": True,
                "update_mode": "incremental_with_reorganize",
                "accumulation_only": True,
            },
        }
        (task / "review_lock.yaml").write_text(json.dumps(lock, ensure_ascii=False), encoding="utf-8")
        (task / "source_manifest.json").write_text('{"version":1,"sources":[],"conflicts":[]}', encoding="utf-8")
        (task / "language_index.json").write_text(
            '{"version":1,"vocabulary":{},"translations":{},"writing":{}}', encoding="utf-8"
        )
        (task / "review_spec.md").write_text("# 语言积累测试\n\n只维护三个积累表。\n", encoding="utf-8")
        (task / "progress-log.md").write_text("# Progress Log\n\n- 当前阶段：已完成交付\n", encoding="utf-8")
        (task / outputs[0]).write_text(
            "# 词汇语法积累表\n\n## 词条：account for\n\n"
            "| 词性 | 英文释义 | 搭配与用法 | 例句 | 同义词/近义词 |\n"
            "| --- | --- | --- | --- | --- |\n"
            "| phr v | to form a part | account for + amount | Sales account for half of the total. | make up |\n"
            "| phr v | to explain a cause | account for + result | Weather may account for the delay. | explain |\n",
            encoding="utf-8",
        )
        (task / outputs[1]).write_text(
            "# 翻译积累表\n\n## 原句：Technology contributes to education.\n\n"
            "- **方向：** 英译中\n- **语义拆分：** Technology / contributes to / education\n"
            "- **译文：** 技术促进教育发展。\n\n| 关键表达 | 翻译说明 |\n| --- | --- |\n"
            "| contribute to | 表示促进。 |\n| education | 表示教育。 |\n",
            encoding="utf-8",
        )
        (task / outputs[2]).write_text(
            "# 写作积累表\n\n| 英文句子 | 中文含义 | 句型结构 | 可替换部分 |\n"
            "| --- | --- | --- | --- |\n",
            encoding="utf-8",
        )
        for label, report in (
            ("内容校验", validate_review(task)),
            ("结构校验", validate_output_structure(task)),
        ):
            if not report["valid"]:
                errors.extend(f"语言积累{label}失败：{error}" for error in report["errors"])


def main() -> int:
    errors: list[str] = []
    required = {
        "SKILL.md": ["原子点标题 → 考查要求 → 分块内容", "所有板块统一执行逐点排版", "文科、理科、工科共享同一内容契约", "inferred", "章节标题、题型目录", "临时目录不得预先创建"],
        "workflows/final-exam.md": ["原子点标题 → 考查要求 → 分块内容", "文科补充背景", "语言类只补充词义", "三个独立积累表"],
        "workflows/contest-review.md": ["大量资料缺失时不逐站联网", "不得把题型目录"],
        "templates/subject-presets/liberal-arts.md": ["概念/背景/原因/内容/影响/评价/论据分块", "标记 `inferred`"],
        "templates/subject-presets/language.md": ["只做语言积累与增量整理", "三个表格独立维护", "最长词组优先拆分", "## 词条："],
        "templates/review-frames/language-summary.md": ["三个表格必须独立", "用户确认前不得修改表格", "英文句子", "## 原句："],
        "templates/review-frames/final-three-files.md": ["文科、理科、工科共用本骨架", "所有学科均采用逐点排版", "长推导逐步换行"],
        "workflows/template-selection.md": ["文科、理科、工科使用同一个", "目录过滤、去重、来源隔离"],
        "scripts/language_accumulator.py": ["已积累", "未积累", "translation_refs", "--confirmed"],
    }
    forbidden = {
        "workflows/final-exam.md": ["考点信息表", "概念型最终显示为 `要点 | 内容` 表格"],
        "templates/subject-presets/language.md": ["板块资料不足：少量联网补足板块总结", "词汇语法 → 阅读"],
        "templates/review-frames/language-summary.md": ["| 要点 | 内容 | 来源 |", "## 阅读"],
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
    check_language_accumulation(errors)

    for error in errors:
        print(f"ERROR: {error}")
    print("PASS" if not errors else "FAIL")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

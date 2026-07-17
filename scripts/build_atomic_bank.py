#!/usr/bin/env python3
"""Build concrete, source-grounded questions for every atomic point."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from source_excerpt import select

PAGE = re.compile(r"(?ms)^## Page (\d+)\s*$(.*?)(?=^## Page |\Z)")
LETTERS = "ABCD"

CALCULATIONS = {
    "AP-P10-02": (
        "【计算】某分类模型在 200 个样本中正确预测了 170 个。计算准确率。",
        "准确率 = 170/200 = 0.85，即 85%。",
    ),
    "AP-P10-03": (
        "【计算】某模型得到 TP=36、FP=9。计算精确率 Precision。",
        "Precision = TP/(TP+FP) = 36/(36+9) = 0.80。",
    ),
    "AP-P10-04": (
        "【计算】已知 TP=60、FN=15、TN=100、FP=25。分别计算召回率和特异度。",
        "Recall = 60/(60+15) = 0.80；Specificity = 100/(100+25) = 0.80。",
    ),
    "AP-P10-05": (
        "【计算】某模型精确率为 0.75、召回率为 0.60。计算 F1 值。",
        "F1 = 2×0.75×0.60/(0.75+0.60) ≈ 0.667。",
    ),
    "AP-P19-03": (
        "【计算】共有 10 笔事务，A 出现 5 次，A 与 B 同时出现 4 次。计算规则 A→B 的支持度和置信度。",
        "支持度 = 4/10 = 0.40；置信度 = 4/5 = 0.80。",
    ),
    "AP-P19-04": (
        "【计算】规则 A→B 的支持度为 0.30、置信度为 0.70；最小支持度为 0.25、最小置信度为 0.75。判断它是否为强规则。",
        "不是强规则。支持度达到阈值，但置信度 0.70<0.75，未同时满足两个阈值。",
    ),
}


def shorten(text: str, limit: int = 170) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else text[:limit].rstrip("，；： ") + "……"


def invert(statement: str) -> tuple[str, bool]:
    replacements = (
        ("不需要", "需要"), ("需要", "不需要"), ("不属于", "属于"), ("属于", "不属于"),
        ("不能", "能"), ("可以", "不可以"), ("没有", "有"), ("存在", "不存在"),
    )
    for old, new in replacements:
        if old in statement:
            return statement.replace(old, new, 1), False
    return statement, True


def fill_blank(statement: str, title: str) -> tuple[str, str]:
    candidates = [
        part.replace("含义", "").strip()
        for part in re.split(r"及其|的|与|、|\s+", title)
        if len(part.replace("含义", "").strip()) >= 2
    ]
    candidates += re.findall(r"[A-Z][A-Za-z-]{1,}|[\u4e00-\u9fff]{2,8}", title)
    candidates += re.findall(r"^([^：:]{2,10})[：:]", statement)
    for term in sorted(set(candidates), key=len, reverse=True):
        if term in statement and term not in {"基本概念", "核心思想", "实现流程", "应用场景"}:
            return statement.replace(term, "____", 1), term
    words = re.findall(r"[\u4e00-\u9fff]{2,6}", statement)
    term = words[0] if words else title
    return statement.replace(term, "____", 1), term


def source_block(items: list[str]) -> list[str]:
    result: list[str] = []
    for index, item in enumerate(items, 1):
        result.append(f"{index}. {item}")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task_dir")
    parser.add_argument("map_file")
    parser.add_argument("--prefix", default="Q")
    args = parser.parse_args()

    task = Path(args.task_dir)
    atoms = json.loads(Path(args.map_file).read_text(encoding="utf-8"))["atoms"]
    source_cache: dict[str, dict[int, str]] = {}
    atom_items: list[list[str]] = []
    for atom in atoms:
        source_id = atom["source_id"]
        if source_id not in source_cache:
            source_path = next((task / "sources").glob(f"{source_id}.md"))
            text = source_path.read_text(encoding="utf-8")
            source_cache[source_id] = {
                int(match.group(1)): match.group(2).strip() for match in PAGE.finditer(text)
            }
        pages = [source_cache[source_id][page] for page in atom["pages"]]
        atom_items.append(atom.get("extracts") or select(pages, atom["title"], atom["action"]))
    clean_distractor_pool = [
        shorten(items[0])
        for atom, items in zip(atoms, atom_items)
        if atom.get("extracts") and items
    ]

    questions = ["# 题目", "", "按原子考点组织；题干基于对应来源内容生成。"]
    answers = ["# 答案", "", "答案与题目 ID 一一对应，包含结论及必要依据。"]
    number = 1

    for atom_index, atom in enumerate(atoms):
        atomic_id, title, action = atom["id"], atom["title"], atom["action"]
        items = atom_items[atom_index]
        source = f"{atom['source_id']}#" + ",".join(f"Page-{p}" for p in atom["pages"])
        questions.extend(["", f"### {atomic_id} {title}"])
        answers.extend(["", f"### {atomic_id} {title}"])

        # 1. Choice: one statement belongs to this atomic point; distractors come
        # from other atomic points, so every option is meaningful rather than filler.
        correct = shorten(items[0])
        distractors: list[str] = []
        cursor = atom_index + 1
        while len(distractors) < 3:
            candidate = clean_distractor_pool[cursor % len(clean_distractor_pool)]
            if candidate != correct and candidate not in distractors:
                distractors.append(candidate)
            cursor += 7
        correct_pos = atom_index % 4
        options = distractors[:]
        options.insert(correct_pos, correct)
        qid = f"{args.prefix}-{number:03d}"
        questions.extend([
            f"<!-- question_id: {qid} atomic_id: {atomic_id} type: choice difficulty: basic source: generated -->",
            f"1. 【选择】下列哪一项直接描述了“{title}”？",
            "",
            *[
                line
                for i, option in enumerate(options)
                for line in [f"{LETTERS[i]}：{option}", ""]
            ],
        ])
        answers.extend([
            "", f"<!-- answer_id: {qid} atomic_id: {atomic_id} -->",
            f"#### {qid}｜选择题", "",
            f"- **答案：** {LETTERS[correct_pos]}", "",
            f"- **解析：** {correct}", "",
            f"- **来源：** `{source}`",
        ])
        number += 1

        # 2. Judgment/fill alternate to avoid a mechanically identical bank.
        statement = shorten(items[min(1, len(items) - 1)])
        qid = f"{args.prefix}-{number:03d}"
        if atom_index % 2 == 0:
            judged, is_true = invert(statement)
            questions.extend([
                f"<!-- question_id: {qid} atomic_id: {atomic_id} type: judgment difficulty: medium source: generated -->",
                f"2. 【判断】{judged}（ ）",
            ])
            answers.extend([
                "", f"<!-- answer_id: {qid} atomic_id: {atomic_id} -->",
                f"#### {qid}｜判断题", "",
                f"- **结论：** {'正确' if is_true else '错误'}", "",
                f"- **订正：** {statement}", "",
                f"- **来源：** `{source}`",
            ])
        else:
            blanked, term = fill_blank(statement, title)
            questions.extend([
                f"<!-- question_id: {qid} atomic_id: {atomic_id} type: fill_blank difficulty: medium source: generated -->",
                f"2. 【填空】{blanked}",
            ])
            answers.extend([
                "", f"<!-- answer_id: {qid} atomic_id: {atomic_id} -->",
                f"#### {qid}｜填空题", "",
                f"- **答案：** {term}", "",
                f"- **完整表述：** {statement}", "",
                f"- **来源：** `{source}`",
            ])
        number += 1

        # 3. Calculation where appropriate; otherwise ask a point-specific
        # procedure or short-answer question and provide the concrete source points.
        qid = f"{args.prefix}-{number:03d}"
        if atomic_id in CALCULATIONS:
            prompt, answer = CALCULATIONS[atomic_id]
            qtype = "calculation"
            questions.extend([
                f"<!-- question_id: {qid} atomic_id: {atomic_id} type: {qtype} difficulty: advanced source: generated -->",
                f"3. {prompt}",
            ])
            answers.extend([
                "", f"<!-- answer_id: {qid} atomic_id: {atomic_id} -->",
                f"#### {qid}｜计算题", "",
                f"- **计算过程：** {answer}", "",
                f"- **来源：** `{source}`",
            ])
        elif any(key in action + title for key in ("步骤", "流程", "计算过程", "实现过程")):
            questions.extend([
                f"<!-- question_id: {qid} atomic_id: {atomic_id} type: short_answer difficulty: advanced source: generated -->",
                f"3. 【简答】按照正确顺序写出“{title}”的主要步骤。",
            ])
            answers.extend([
                "", f"<!-- answer_id: {qid} atomic_id: {atomic_id} -->",
                f"#### {qid}｜简答题", "",
                "**参考答案：**", "",
                *[f"- {item}" for item in items], "",
                f"**来源：** `{source}`",
            ])
        else:
            questions.extend([
                f"<!-- question_id: {qid} atomic_id: {atomic_id} type: short_answer difficulty: advanced source: generated -->",
                f"3. 【简答】针对“{title}”，回答以下要点：{action}。",
            ])
            answers.extend([
                "", f"<!-- answer_id: {qid} atomic_id: {atomic_id} -->",
                f"#### {qid}｜简答题", "",
                "**参考答案：**", "",
                *[f"- {item}" for item in items], "",
                f"**来源：** `{source}`",
            ])
        number += 1

    (task / "题目.md").write_text("\n".join(questions) + "\n", encoding="utf-8")
    (task / "答案.md").write_text("\n".join(answers) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Build concrete, source-grounded questions for every atomic point."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from source_excerpt import select

SECTION = re.compile(r"(?ms)^## (Page|Slide) (\d+)\s*$(.*?)(?=^## (?:Page|Slide) |\Z)")
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
    if words:
        term = words[0]
        return statement.replace(term, "____", 1), term
    return f"____：{statement}", title


def source_block(items: list[str]) -> list[str]:
    result: list[str] = []
    for index, item in enumerate(items, 1):
        result.append(f"{index}. {item}")
    return result


def enrichment_items(entry: dict) -> list[str]:
    return [item for block in entry.get("blocks", []) for item in block.get("items", [])]


def false_variants(statement: str) -> list[str]:
    """Create same-topic distractors by changing one operative condition."""
    swaps = (
        ("∈", "⊆"), ("⊆", "∈"), ("∪", "∩"), ("∩", "∪"),
        ("∧", "∨"), ("∨", "∧"), ("⇔", "⇒"), ("⇒", "⇔"),
        ("每个", "至少一个"), ("至少一个", "每个"), ("所有", "某些"),
        ("恰好", "至少"), ("相同", "相反"), ("偶数", "奇数"),
        ("n−1", "n+1"), ("先", "最后"), ("不含", "必须含有"),
        ("存在", "不存在"), ("可以", "不可以"), ("唯一", "不唯一"),
        ("2ⁿ", "n²"), ("n!", "n"), ("n−1", "n+1"),
        ("为 1", "为 0"), ("为 0", "为 1"), ("大于等于", "小于等于"),
        ("是", "不是"), ("称为", "不称为"), ("要求", "不要求"),
        ("同时", "只需任意一个"), ("回到", "不回到"),
        ("简单", "复合"), ("分别", "统一"), ("确定", "忽略"),
        ("添加", "删除"), ("根据", "不考虑"), ("对应", "无关"),
        ("顶点", "边"), ("有向", "无向"), ("自环", "平行边"),
        ("画", "删除"), ("发出", "指向"), ("行", "列"),
        ("自反性", "反自反性"), ("反对称性", "对称性"),
        ("传递性", "非传递性"), ("可比较", "不可比较"),
        ("入度", "出度"), ("出度", "入度"), ("指向", "离开"),
        ("相加", "相减"), ("最小", "最大"), ("从小到大", "从大到小"),
        ("删除", "保留"), ("减", "加"), ("大于", "小于"),
        ("负数", "正数"), ("全部", "部分"), ("非增", "非减"),
        ("≤", "≥"), ("≥", "≤"), ("+", "−"),
        ("两个", "三个"), ("叶", "根"), ("最终", "最初"),
        ("左", "右"), ("右", "左"), ("相乘", "相加"),
        ("互斥", "可以重叠"), ("连续步骤", "互斥分类"),
        ("总方法数", "平均方法数"), ("各块", "任意一块"),
        ("每一步", "任意一步"), ("依次", "任选"), ("所有步骤", "任一步骤"),
        ("第 i 步", "任意一步"), ("分 k 个", "不分"),
        ("n₁n₂⋯nₖ", "n₁+n₂+⋯+nₖ"),
    )
    result: list[str] = []
    for old, new in swaps:
        if old in statement:
            candidate = statement.replace(old, new, 1)
            if candidate != statement and candidate not in result:
                result.append(candidate)
    if "=" in statement:
        candidate = statement.replace("=", "≠", 1)
        if candidate not in result:
            result.append(candidate)
    if "2ⁿ" in statement:
        result.append(statement.replace("2ⁿ", "2n", 1))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task_dir")
    parser.add_argument("map_file")
    parser.add_argument("--prefix", default="Q")
    args = parser.parse_args()

    task = Path(args.task_dir)
    atoms = json.loads(Path(args.map_file).read_text(encoding="utf-8"))["atoms"]
    enrichment: dict = {}
    for filename in ("knowledge_enrichment.json", "knowledge_inferred.json"):
        path = task / filename
        if path.exists():
            enrichment.update(json.loads(path.read_text(encoding="utf-8")))
    source_cache: dict[str, tuple[str, dict[int, str]]] = {}
    atom_items: list[list[str]] = []
    for atom in atoms:
        source_id = atom["source_id"]
        if source_id not in source_cache:
            source_path = next((task / "sources").glob(f"{source_id}.md"))
            text = source_path.read_text(encoding="utf-8")
            matches = list(SECTION.finditer(text))
            kind = matches[0].group(1) if matches else "Page"
            source_cache[source_id] = (
                kind,
                {int(match.group(2)): match.group(3).strip() for match in matches},
            )
        _, sections = source_cache[source_id]
        pages = [sections[page] for page in atom["pages"]]
        inferred_items = enrichment_items(enrichment.get(atom["id"], {}))
        atom_items.append(inferred_items or atom.get("extracts") or select(pages, atom["title"], atom["action"]))
    missing_content = [atom["id"] for atom, items in zip(atoms, atom_items) if not items]
    if missing_content:
        raise ValueError(
            "以下原子考点只有章节目录或题型提示，不能据此自动出题："
            + ", ".join(missing_content)
            + "。请先补充定义、公式或规则并进行语义审题。"
        )
    questions = ["# 题目", "", "按原子考点组织；题干基于对应来源内容生成。"]
    answers = ["# 答案", "", "答案与题目 ID 一一对应，包含结论及必要依据。"]
    question_manifest: list[dict[str, str]] = []
    number = 1

    for atom_index, atom in enumerate(atoms):
        atomic_id, title, action = atom["id"], atom["title"], atom["action"]
        items = atom_items[atom_index]
        section_kind = source_cache[atom["source_id"]][0]
        source = (
            "inferred（模型知识补全）" if atomic_id in enrichment
            else f"{atom['source_id']}#" + ",".join(f"{section_kind}-{p}" for p in atom["pages"])
        )
        questions.extend(["", f"### {atomic_id} {title}"])
        answers.extend(["", f"### {atomic_id} {title}"])

        # 1. Choice: all options stay on the current atomic point. Distractors
        # alter exactly one operative condition in the correct statement.
        correct = shorten(items[0])
        distractors: list[str] = []
        for statement_candidate in items:
            for candidate in false_variants(shorten(statement_candidate)):
                if candidate != correct and candidate not in distractors:
                    distractors.append(candidate)
        if len(distractors) < 3:
            raise ValueError(f"{atomic_id} 无法生成 3 个同层级有效干扰项，请补充该考点的易错规则")
        distractors = distractors[:3]
        correct_pos = atom_index % 4
        options = distractors[:]
        options.insert(correct_pos, correct)
        qid = f"{args.prefix}-{number:03d}"
        question_manifest.append({"question_id": qid, "atomic_id": atomic_id, "type": "choice", "difficulty": "basic", "source": "generated"})
        questions.extend([
            f"#### {qid}｜选择题", "",
            f"【选择】关于“{title}”，下列说法正确的是？",
            "",
            *[
                line
                for i, option in enumerate(options)
                for line in [f"{LETTERS[i]}：{option}", ""]
            ],
        ])
        answers.extend([
            "", f"#### {qid}｜选择题", "",
            f"- **答案：** {LETTERS[correct_pos]}", "",
            f"- **解析：** {correct}", "",
            f"- **来源：** `{source}`",
        ])
        number += 1

        # 2. Judgment/fill alternate to avoid a mechanically identical bank.
        statement = shorten(items[min(1, len(items) - 1)])
        qid = f"{args.prefix}-{number:03d}"
        if atom_index % 2 == 0:
            question_manifest.append({"question_id": qid, "atomic_id": atomic_id, "type": "judgment", "difficulty": "medium", "source": "generated"})
            if atom_index % 4 == 0:
                judged, is_true = statement, True
            else:
                judged, is_true = false_variants(statement)[0], False
            questions.extend([
                f"#### {qid}｜判断题", "",
                f"【判断】{judged}（ ）",
            ])
            answers.extend([
                "", f"#### {qid}｜判断题", "",
                f"- **结论：** {'正确' if is_true else '错误'}", "",
                f"- **订正：** {statement}", "",
                f"- **来源：** `{source}`",
            ])
        else:
            question_manifest.append({"question_id": qid, "atomic_id": atomic_id, "type": "fill_blank", "difficulty": "medium", "source": "generated"})
            blanked, term = fill_blank(statement, title)
            questions.extend([
                f"#### {qid}｜填空题", "",
                f"【填空】{blanked}",
            ])
            answers.extend([
                "", f"#### {qid}｜填空题", "",
                f"- **答案：** {term}", "",
                f"- **完整表述：** {statement}", "",
                f"- **来源：** `{source}`",
            ])
        number += 1

        # 3. Calculation where appropriate; otherwise ask a point-specific
        # procedure or short-answer question and provide the concrete source points.
        qid = f"{args.prefix}-{number:03d}"
        if atomic_id == "AP-052":
            question_manifest.append({"question_id": qid, "atomic_id": atomic_id, "type": "design", "difficulty": "advanced", "source": "generated"})
            questions.extend([
                f"#### {qid}｜方案设计题", "",
                "【方案设计】设计一个通用GET采集函数：接收URL、查询参数和请求头，发送请求后检查状态码，并返回响应文本。写出核心代码和处理步骤。",
            ])
            answers.extend([
                "", f"#### {qid}｜方案设计题", "",
                "**参考答案：**", "",
                "- 使用 `import requests` 导入模块。",
                "- 定义函数参数 `url`、`params=None`、`headers=None`。",
                "- 调用 `response = requests.get(url, params=params, headers=headers)`。",
                "- 使用 `response.raise_for_status()` 或检查 `response.status_code` 处理请求失败。",
                "- 返回 `response.text`；二进制内容可改用 `response.content`。", "",
                f"**来源：** `{source}`",
            ])
        elif atomic_id in CALCULATIONS:
            prompt, answer = CALCULATIONS[atomic_id]
            qtype = "calculation"
            question_manifest.append({"question_id": qid, "atomic_id": atomic_id, "type": qtype, "difficulty": "advanced", "source": "generated"})
            questions.extend([
                f"#### {qid}｜计算题", "", prompt,
            ])
            answers.extend([
                "", f"#### {qid}｜计算题", "",
                f"- **计算过程：** {answer}", "",
                f"- **来源：** `{source}`",
            ])
        elif any(key in action + title for key in ("步骤", "流程", "计算过程", "实现过程")):
            question_manifest.append({"question_id": qid, "atomic_id": atomic_id, "type": "short_answer", "difficulty": "advanced", "source": "generated"})
            questions.extend([
                f"#### {qid}｜简答题", "",
                f"【简答】按照正确顺序写出“{title}”的主要步骤。",
            ])
            answers.extend([
                "", f"#### {qid}｜简答题", "",
                "**参考答案：**", "",
                *[f"- {item}" for item in items], "",
                f"**来源：** `{source}`",
            ])
        else:
            question_manifest.append({"question_id": qid, "atomic_id": atomic_id, "type": "short_answer", "difficulty": "advanced", "source": "generated"})
            if "证明" in action:
                applied_prompt = f"写出“{title}”使用的规则，并按逻辑顺序说明证明过程。"
            elif "计算" in action:
                applied_prompt = f"写出“{title}”的计算公式或算法，并说明各符号和计算顺序。"
            else:
                applied_prompt = f"写出“{title}”的关键结论，并分别说明其{action.replace('/', '、')}。"
            questions.extend([
                f"#### {qid}｜简答题", "",
                f"【简答】{applied_prompt}",
            ])
            answers.extend([
                "", f"#### {qid}｜简答题", "",
                "**参考答案：**", "",
                *[f"- {item}" for item in items], "",
                f"**来源：** `{source}`",
            ])
        number += 1

    (task / "题目.md").write_text("\n".join(questions) + "\n", encoding="utf-8")
    (task / "答案.md").write_text("\n".join(answers) + "\n", encoding="utf-8")
    (task / "question_manifest.json").write_text(
        json.dumps({"version": 1, "questions": question_manifest}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

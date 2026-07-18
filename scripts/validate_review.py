#!/usr/bin/env python3
"""Validate task artifacts, stable IDs, coverage, sources, and difficulty."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from validate_output_structure import validate as validate_output_structure

HEADING = re.compile(r"^(#{3,6})\s+(.+?)\s*$", re.M)
Q_META = re.compile(r"<!--\s*question_id:\s*([A-Za-z0-9_-]+)(.*?)-->")
A_META = re.compile(r"<!--\s*answer_id:\s*([A-Za-z0-9_-]+)(.*?)-->")
ATOMIC_ROW = re.compile(r"^\|\s*(AP-[A-Za-z0-9_-]+)\s*\|", re.M)
KNOWLEDGE_SECTION = re.compile(r"(?ms)^###\s+(AP-[A-Za-z0-9_-]+)｜([^\n]+)\n(.*?)(?=^###\s+AP-|^##\s+|\Z)")
SOURCE_REF = re.compile(r"(SRC-\d{3})(?:#[^\s，。；;)）]+)?")
BROKEN_MATH = re.compile(
    r"\?{2,}|\?[A-Za-z0-9]|[\u200b-\u200d\uE000-\uF8FF\uFFFD]"
    r"|[➢]"
    r"|[]"
)
VISUAL_NOISE = re.compile(
    r"输入0|输出0|-0\.5\s+-0\.5|数据预处理章节|Ø|NO!|分类任务训练数据"
)
SKELETON_QUESTION = re.compile(
    r"完整说明.+定义、核心内容和作用|围绕.+逐项完成以下考查要求|结合一个数据挖掘场景，说明如何运用"
)
LOW_QUALITY_JUDGMENT = re.compile(r"课程材料未提及以下内容")
EXAM_TYPE_LEAK = re.compile(r"选择[、，,]?填空|填空[、，,]?判断|判断题|计算题与证明题|•\s*知识点")
QUESTION_OUTLINE_LEAK = re.compile(
    r"符合课程材料|课程材料未提及|以下内容与本考点无关|第[一二三四五六七八九十]+章.{0,30}(?:选择|填空|判断|知识点)|"
    r"(?:选择|填空|判断)题.{0,12}知识点"
)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def load_json(path: Path, errors: list[str]) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append(f"缺少文件：{path.name}")
    except json.JSONDecodeError as exc:
        errors.append(f"{path.name} 无法解析：{exc}")
    return {}


def blocks_with_question_ids(text: str) -> list[tuple[str, list[str]]]:
    headings = list(HEADING.finditer(text))
    result = []
    for index, heading in enumerate(headings):
        level = len(heading.group(1))
        end = len(text)
        for later in headings[index + 1:]:
            if len(later.group(1)) <= level:
                end = later.start()
                break
        ids = [m.group(1) for m in Q_META.finditer(text, heading.end(), end)]
        if ids:
            result.append((heading.group(2).strip(), ids))
    return result


def duplicates(values: list[str]) -> list[str]:
    return sorted({value for value in values if values.count(value) > 1})


def meta_value(match: re.Match[str], key: str) -> str | None:
    found = re.search(rf"\b{re.escape(key)}:\s*([A-Za-z0-9_-]+)", match.group(2))
    return found.group(1) if found else None


def validate(task_dir: Path) -> dict:
    task_dir = task_dir.resolve()
    if not task_dir.is_dir():
        raise ValueError(f"任务目录不存在：{task_dir}")
    errors: list[str] = []
    warnings: list[str] = []
    structure_report = validate_output_structure(task_dir)
    errors.extend(f"结构校验：{error}" for error in structure_report["errors"])
    lock = load_json(task_dir / "review_lock.yaml", errors)
    manifest = load_json(task_dir / "source_manifest.json", errors)
    for filename in ("review_spec.md", "progress-log.md"):
        if not read(task_dir / filename).strip():
            errors.append(f"缺少或为空：{filename}")

    outputs = lock.get("outputs", [])
    for filename in outputs:
        if not read(task_dir / filename).strip():
            errors.append(f"合同产物缺少或为空：{filename}")
    mode = lock.get("task", {}).get("mode")
    category = lock.get("task", {}).get("category")
    minimum = lock.get("rules", {}).get("minimum_questions_per_point", 3)
    if lock.get("rules", {}).get("full_pipeline_required") is not True:
        errors.append("合同未启用 full_pipeline_required，不能按完整 skill 流程交付")

    source_ids = {item.get("source_id") for item in manifest.get("sources", [])}
    scope_control = lock.get("scope_control", {})
    declared_primary = scope_control.get("primary_sources", [])
    unknown_primary = [source for source in declared_primary if source.startswith("SRC-") and source not in source_ids]
    if unknown_primary:
        errors.append(f"合同声明的 primary 来源未登记：{', '.join(unknown_primary)}")
    if "USER-OUTLINE" in scope_control.get("primary_sources", []):
        if not any(item.get("kind") == "user_text" and item.get("role") == "primary" for item in manifest.get("sources", [])):
            errors.append("合同把用户大纲列为 primary，但 source_manifest.json 缺少 primary user_text 来源")
    for item in manifest.get("sources", []):
        if item.get("status") in {"needs_conversion", "needs_ocr", "failed"}:
            warnings.append(f"来源 {item.get('source_id')} 状态为 {item.get('status')}")

    question_file = "新题答案.md" if mode == "contest" else "题目.md"
    question_text = read(task_dir / question_file)
    if SKELETON_QUESTION.search(question_text):
        errors.append("题目.md 仍包含未加工的通用骨架题干")
    if LOW_QUALITY_JUDGMENT.search(question_text):
        errors.append("题目.md 包含以‘材料是否提及’代替知识判断的低质量判断题")
    leaked_question_outline = QUESTION_OUTLINE_LEAK.search(question_text)
    if leaked_question_outline:
        errors.append(f"题目.md 把章节目录或‘是否符合材料’当成题干/选项：{leaked_question_outline.group(0)!r}")

    knowledge_text = read(task_dir / "知识点.md")
    leaked_exam_type = EXAM_TYPE_LEAK.search(knowledge_text)
    if leaked_exam_type:
        errors.append(f"知识点.md 混入题型或章节目录文字：{leaked_exam_type.group(0)!r}")
    for atomic_id, title, body in KNOWLEDGE_SECTION.findall(knowledge_text):
        requirement = re.search(r"考查要求：\*\*\s*([^\n]+)", body)
        action = requirement.group(1).strip() if requirement else ""
        content = re.sub(r">\s*\*\*考查要求：\*\*[^\n]*", "", body).strip()
        plain = re.sub(r"[#>*`\-\d.\s]", "", content)
        if len(plain) < 40:
            errors.append(f"{atomic_id} {title} 内容不足：只有名称或短句，尚不能用于复习")
            continue
        if any(key in action for key in ("计算", "证明")):
            has_rule = re.search(
                r"[=⇔⇒→∧∨¬∀∃ΣΠ]|步骤|推导|算法|条件|性质|判定|证明|构造|矩阵|"
                r"当且仅当|充要|次序|排列数|极大元|极小元|选取|合并",
                content,
            )
            if not has_rule:
                errors.append(f"{atomic_id} {title} 缺少公式、规则或可执行步骤")
    choice_count = len(re.findall(r"【选择】", question_text))
    for label in "ABCD":
        option_count = len(re.findall(rf"(?m)^{label}：.+$", question_text))
        if option_count != choice_count:
            errors.append(
                f"选择题格式错误：{choice_count} 道选择题，但识别到 {option_count} 个 {label} 选项"
            )
    rendered_breaks = len(re.findall(r"(?ms)【选择】[^\n]+\n\nA：.+?\n\nB：.+?\n\nC：.+?\n\nD：", question_text))
    if rendered_breaks != choice_count:
        errors.append(
            f"选择题 Markdown 空行格式错误：{choice_count} 道题，仅 {rendered_breaks} 道可在预览中正确分段"
        )
    question_manifest = load_json(task_dir / "question_manifest.json", errors)
    q_records = question_manifest.get("questions", [])
    q_ids = [item.get("question_id") for item in q_records if item.get("question_id")]
    visible_q_ids = re.findall(
        r"(?m)^####\s+([A-Za-z0-9_-]+)｜(?:选择题|判断题|填空题|简答题|计算题|方案设计题)$",
        question_text,
    )
    if question_file in outputs:
        if not q_ids:
            errors.append("question_manifest.json 未识别到 question_id，无法核验题量和同步")
        if visible_q_ids != q_ids:
            errors.append(f"{question_file} 的可见题号与 question_manifest.json 不同步")
        for duplicate in duplicates(q_ids):
            errors.append(f"重复 question_id：{duplicate}")

    # A final-exam task with an atomic-point map must prove coverage per atomic ID,
    # rather than merely counting questions under a broad chapter heading.
    atomic_text = read(task_dir / "atomic_points.md")
    atomic_ids = ATOMIC_ROW.findall(atomic_text)
    if atomic_text and not atomic_ids:
        errors.append("atomic_points.md 未识别到 atomic_id 表格行")
    for atomic_id in atomic_ids:
        knowledge_text = read(task_dir / "知识点.md")
        heading = re.search(rf"^###\s+{re.escape(atomic_id)}\b.*$", knowledge_text, re.M)
        if not heading:
            errors.append(f"知识点.md 缺少原子考点标题：{atomic_id}")
        else:
            next_heading = re.search(r"^###\s+", knowledge_text[heading.end():], re.M)
            end = heading.end() + next_heading.start() if next_heading else len(knowledge_text)
            block = knowledge_text[heading.end():end]
            if "> **考查要求：**" not in block or not re.search(r"(?m)^####\s+.+$", block):
                errors.append(f"知识点 {atomic_id} 未使用‘考查要求＋分块内容’结构")
            content_rows = re.findall(r"(?m)^- .+$", block)
            numbered_steps = re.findall(r"(?m)^\d+\. .+$", block)
            content = "\n".join(content_rows + numbered_steps)
            if not content.strip():
                errors.append(f"知识点 {atomic_id} 缺少必背内容")
            if len(content) > 2200:
                errors.append(f"知识点 {atomic_id} 摘录过长，疑似整页复制")
        atomic_questions = [item for item in q_records if item.get("atomic_id") == atomic_id]
        if len(atomic_questions) < minimum:
            errors.append(f"原子考点 {atomic_id} 只有 {len(atomic_questions)} 题，少于 {minimum} 题")
    if atomic_ids and len(q_ids) < len(atomic_ids) * minimum:
        errors.append(f"题库总题数 {len(q_ids)} 少于原子点下限 {len(atomic_ids) * minimum}")
    if atomic_ids:
        spec_text = read(task_dir / "review_spec.md")
        progress_text = read(task_dir / "progress-log.md")
        for filename, text in (("review_spec.md", spec_text), ("progress-log.md", progress_text)):
            if str(len(atomic_ids)) not in text or str(len(q_ids)) not in text:
                errors.append(
                    f"{filename} 未同步当前规模：{len(atomic_ids)} 个原子点、{len(q_ids)} 题"
                )

    atomic_map_path = task_dir / "atomic_map.json"
    if atomic_map_path.is_file():
        atomic_map = load_json(atomic_map_path, errors)
        mapped_ids = [item.get("id") for item in atomic_map.get("atoms", [])]
        if mapped_ids != atomic_ids:
            errors.append("atomic_points.md 与 atomic_map.json 的原子点 ID 或顺序不一致")
        parents = {item.get("parent") for item in atomic_map.get("atoms", [])}
        expected_parents = set(atomic_map.get("outline_parents", []))
        if expected_parents:
            missing_parents = sorted(expected_parents - parents)
            if missing_parents:
                errors.append(f"原子点未覆盖全部大纲条目：{', '.join(missing_parents)}")

    if mode == "final_exam" and category != "language":
        answer_text = read(task_dir / "答案.md")
        answer_ids = re.findall(
            r"(?m)^####\s+([A-Za-z0-9_-]+)｜(?:选择题|判断题|填空题|简答题|计算题|方案设计题)$",
            answer_text,
        )
        if q_ids != answer_ids:
            errors.append("题目与答案的稳定 ID 或顺序不一致")
        answer_headings = answer_ids
        if answer_headings != answer_ids:
            errors.append("答案未按 question_id｜题型 使用独立标题，或标题顺序不一致")
        if re.search(r"(?m)^[123]\.\s+\*\*(?:答案|结论|参考答案|计算过程)", answer_text):
            errors.append("答案仍使用循环的 1、2、3 编号")
    if category == "language":
        summary = read(task_dir / "复习总结.md")
        missing = [x for x in ("词汇语法", "阅读", "翻译", "写作") if x not in summary]
        if missing:
            errors.append(f"复习总结缺少板块：{'、'.join(missing)}")
    if mode == "contest":
        outline = read(task_dir / "提纲.md")
        if "已考点" not in outline or "遗漏点" not in outline:
            errors.append("竞赛提纲必须同时包含已考点和遗漏点")
    if "思维导图.md" in outputs:
        mindmap_text = read(task_dir / "思维导图.md")
        if "![" not in mindmap_text or not (task_dir / "思维导图.png").exists():
            errors.append("思维导图.md 未嵌入可直接查看的思维导图图片")

    all_text = "\n".join(read(task_dir / filename) for filename in outputs)
    normalized_sources = "\n".join(
        read(task_dir / item["normalized_path"])
        for item in manifest.get("sources", [])
        if item.get("normalized_path")
    )
    broken = BROKEN_MATH.search(all_text + "\n" + normalized_sources)
    if broken:
        errors.append(f"正式产物包含未处理的 PDF 公式乱码：{broken.group(0)!r}")
    visual_noise = VISUAL_NOISE.search(all_text)
    if visual_noise:
        errors.append(f"正式产物包含图表标签或示意数据污染：{visual_noise.group(0)!r}")
    unknown_refs = sorted(set(SOURCE_REF.findall(all_text)) - source_ids)
    if unknown_refs:
        errors.append(f"引用了 manifest 中不存在的来源：{', '.join(unknown_refs)}")

    blueprint = lock.get("exam_blueprint")
    # Official distributions describe an exam paper.  They are not an upper limit
    # for an atomic training bank, which intentionally has several questions per point.
    if blueprint and lock.get("rules", {}).get("question_mode") != "atomic_training":
        labels = {
            "single_choice": r"【(?:单选|选择)】",
            "judgment": r"【判断",
            "fill_blank": r"【填空】",
            "short_answer": r"【简答】",
            "calculation": r"【计算",
        }
        for kind, expected in blueprint.get("question_counts", {}).items():
            actual = len(re.findall(labels.get(kind, r"$^"), question_text, re.M))
            if actual != expected:
                errors.append(f"官方题型蓝图不匹配：{kind} 需要 {expected} 题，实际 {actual} 题")
        expected_total = sum(blueprint.get("question_counts", {}).values())
        if expected_total and len(q_ids) != expected_total:
            errors.append(f"官方题型蓝图总题数需要 {expected_total}，实际 {len(q_ids)}")

    levels = [item.get("difficulty") for item in q_records if item.get("difficulty")]
    if levels and not blueprint:
        total = len(levels)
        target = lock.get("rules", {}).get("difficulty_ratio", {})
        for level in ("basic", "medium", "advanced"):
            actual = levels.count(level) / total
            if abs(actual - target.get(level, actual)) > 0.15:
                warnings.append(f"难度比例 {level}={actual:.0%} 偏离合同目标")

    report = {
        "task_dir": str(task_dir),
        "mode": mode,
        "category": category,
        "valid": not errors,
        "metrics": {
            "sources": len(source_ids),
            "questions": len(q_ids),
            "unresolved_sources": sum(
                item.get("status") in {"needs_conversion", "needs_ocr", "failed"}
                for item in manifest.get("sources", [])
            ),
        },
        "errors": errors,
        "warnings": warnings,
    }
    (task_dir / "quality_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task_dir")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        report = validate(Path(args.task_dir))
    except (OSError, ValueError) as exc:
        print(f"[validate-review] ERROR: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for error in report["errors"]:
            print(f"ERROR: {error}")
        for warning in report["warnings"]:
            print(f"WARN: {warning}")
        print("PASS" if report["valid"] else "FAIL")
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Query and update the three Markdown-only language accumulation tables."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

VOCAB_FILE = "词汇语法积累表.md"
TRANSLATION_FILE = "翻译积累表.md"
WRITING_FILE = "写作积累表.md"
INDEX_FILE = "language_index.json"


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold().strip()
    return re.sub(r"\s+", " ", value)


def escape_cell(value: str) -> str:
    return value.strip().replace("|", r"\|").replace("\n", "<br>")


def split_row(line: str) -> list[str]:
    line = line.strip()
    if not line.startswith("|"):
        return []
    result, current, escaped = [], [], False
    for char in line.strip("|"):
        if escaped:
            current.append(char)
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == "|":
            result.append("".join(current).strip())
            current = []
        else:
            current.append(char)
    result.append("".join(current).strip())
    return result


def is_data_row(cells: list[str]) -> bool:
    return bool(cells) and not all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells)


def sections(text: str, label: str) -> list[tuple[str, str, int, int]]:
    pattern = re.compile(rf"(?m)^##\s+{re.escape(label)}：(.+?)\s*$")
    matches = list(pattern.finditer(text))
    result = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        result.append((match.group(1).strip(), text[match.end():end], match.start(), end))
    return result


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def parse_vocabulary(task: Path) -> dict[str, dict]:
    result = {}
    for term, block, _, _ in sections(read(task / VOCAB_FILE), "词条"):
        senses = []
        for line in block.splitlines():
            cells = split_row(line)
            if len(cells) != 5 or cells[0] == "词性" or not is_data_row(cells):
                continue
            senses.append(dict(zip(("pos", "definition", "usage", "example", "synonyms"), cells)))
        key = normalize(term)
        if key in result:
            raise ValueError(f"词汇表存在重复词条分组：{term}")
        result[key] = {"term": term, "senses": senses}
    return result


def parse_translations(task: Path) -> dict[str, dict]:
    result = {}
    for sentence, block, _, _ in sections(read(task / TRANSLATION_FILE), "原句"):
        def field(name: str) -> str:
            match = re.search(rf"(?m)^-\s+\*\*{re.escape(name)}：\*\*\s*(.+?)\s*$", block)
            return match.group(1).strip() if match else ""

        expressions = []
        for line in block.splitlines():
            cells = split_row(line)
            if len(cells) != 2 or cells[0] == "关键表达" or not is_data_row(cells):
                continue
            expressions.append({"expression": cells[0], "explanation": cells[1]})
        key = normalize(sentence)
        if key in result:
            raise ValueError(f"翻译表存在重复原句分组：{sentence}")
        result[key] = {
            "sentence": sentence,
            "direction": field("方向"),
            "segments": field("语义拆分"),
            "translation": field("译文"),
            "expressions": expressions,
        }
    return result


def parse_writing(task: Path) -> dict[str, dict]:
    result = {}
    for line in read(task / WRITING_FILE).splitlines():
        cells = split_row(line)
        if len(cells) != 4 or cells[0] == "英文句子" or not is_data_row(cells):
            continue
        key = normalize(cells[0])
        if key in result:
            raise ValueError(f"写作表存在重复英文句子：{cells[0]}")
        result[key] = dict(zip(("sentence", "meaning", "structure", "replaceable"), cells))
    return result


def contains_term(text: str, term: str) -> bool:
    haystack, needle = normalize(text), normalize(term)
    if not needle:
        return False
    return bool(re.search(rf"(?<![a-z0-9]){re.escape(needle)}(?![a-z0-9])", haystack))


def rebuild(task: Path) -> dict:
    vocabulary = parse_vocabulary(task)
    translations = parse_translations(task)
    writing = parse_writing(task)
    for item in vocabulary.values():
        item["translation_refs"] = []
        item["writing_refs"] = []
        for translation in translations.values():
            searchable = " ".join([
                translation["sentence"], translation["translation"],
                " ".join(exp["expression"] for exp in translation["expressions"]),
            ])
            if contains_term(searchable, item["term"]):
                item["translation_refs"].append(translation["sentence"])
        for sentence in writing.values():
            if contains_term(sentence["sentence"], item["term"]):
                item["writing_refs"].append(sentence["sentence"])
    index = {
        "version": 1,
        "vocabulary": vocabulary,
        "translations": translations,
        "writing": writing,
    }
    (task / INDEX_FILE).write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return index


def status(task: Path, terms: list[str]) -> dict:
    index = rebuild(task)
    result = []
    for term in terms:
        item = index["vocabulary"].get(normalize(term))
        result.append({
            "term": term,
            "status": "已积累" if item else "未积累",
            "sense_count": len(item["senses"]) if item else 0,
            "translation_refs": item["translation_refs"] if item else [],
            "writing_refs": item["writing_refs"] if item else [],
        })
    return {"terms": result}


def require_confirmed(args: argparse.Namespace) -> None:
    if not args.confirmed:
        raise ValueError("写入前必须获得用户确认，并传入 --confirmed")


def append_to_section(text: str, label: str, key: str, row: str) -> tuple[str, bool]:
    for title, block, start, end in sections(text, label):
        if normalize(title) != normalize(key):
            continue
        if normalize(row) in normalize(block):
            return text, False
        updated = text[start:end].rstrip() + "\n" + row + "\n\n"
        return text[:start] + updated + text[end:].lstrip("\n"), True
    return text, False


def add_vocab(task: Path, args: argparse.Namespace) -> dict:
    require_confirmed(args)
    path = task / VOCAB_FILE
    text = read(path) or "# 词汇语法积累表\n"
    row = "| " + " | ".join(escape_cell(value) for value in (
        args.pos, args.definition, args.usage, args.example, args.synonyms
    )) + " |"
    updated, changed = append_to_section(text, "词条", args.term, row)
    if not any(normalize(title) == normalize(args.term) for title, *_ in sections(text, "词条")):
        block = (
            f"\n\n## 词条：{args.term.strip()}\n\n"
            "| 词性 | 英文释义 | 搭配与用法 | 例句 | 同义词/近义词 |\n"
            "| --- | --- | --- | --- | --- |\n"
            f"{row}\n"
        )
        updated, changed = text.rstrip() + block, True
    if changed:
        path.write_text(updated.rstrip() + "\n", encoding="utf-8")
    rebuild(task)
    return {"status": "added" if changed else "duplicate", "term": args.term}


def add_translation(task: Path, args: argparse.Namespace) -> dict:
    require_confirmed(args)
    path = task / TRANSLATION_FILE
    text = read(path) or "# 翻译积累表\n"
    row = f"| {escape_cell(args.expression)} | {escape_cell(args.explanation)} |"
    updated, changed = append_to_section(text, "原句", args.sentence, row)
    if not any(normalize(title) == normalize(args.sentence) for title, *_ in sections(text, "原句")):
        block = (
            f"\n\n## 原句：{args.sentence.strip()}\n\n"
            f"- **方向：** {args.direction.strip()}\n"
            f"- **语义拆分：** {args.segments.strip()}\n"
            f"- **译文：** {args.translation.strip()}\n\n"
            "| 关键表达 | 翻译说明 |\n| --- | --- |\n"
            f"{row}\n"
        )
        updated, changed = text.rstrip() + block, True
    if changed:
        path.write_text(updated.rstrip() + "\n", encoding="utf-8")
    rebuild(task)
    return {"status": "added" if changed else "duplicate", "sentence": args.sentence}


def add_writing(task: Path, args: argparse.Namespace) -> dict:
    require_confirmed(args)
    path = task / WRITING_FILE
    text = read(path) or (
        "# 写作积累表\n\n| 英文句子 | 中文含义 | 句型结构 | 可替换部分 |\n"
        "| --- | --- | --- | --- |\n"
    )
    existing = parse_writing(task)
    if normalize(args.sentence) in existing:
        rebuild(task)
        return {"status": "duplicate", "sentence": args.sentence}
    row = "| " + " | ".join(escape_cell(value) for value in (
        args.sentence, args.meaning, args.structure, args.replaceable
    )) + " |"
    path.write_text(text.rstrip() + "\n" + row + "\n", encoding="utf-8")
    rebuild(task)
    return {"status": "added", "sentence": args.sentence}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    rebuild_parser = sub.add_parser("rebuild")
    rebuild_parser.add_argument("task_dir")
    status_parser = sub.add_parser("status")
    status_parser.add_argument("task_dir")
    status_parser.add_argument("terms", nargs="+")

    vocab = sub.add_parser("add-vocab")
    vocab.add_argument("task_dir")
    vocab.add_argument("--term", required=True)
    vocab.add_argument("--pos", required=True)
    vocab.add_argument("--definition", required=True)
    vocab.add_argument("--usage", required=True)
    vocab.add_argument("--example", required=True)
    vocab.add_argument("--synonyms", default="")
    vocab.add_argument("--confirmed", action="store_true")

    translation = sub.add_parser("add-translation")
    translation.add_argument("task_dir")
    translation.add_argument("--direction", choices=("英译中", "中译英"), required=True)
    translation.add_argument("--sentence", required=True)
    translation.add_argument("--segments", required=True)
    translation.add_argument("--translation", required=True)
    translation.add_argument("--expression", required=True)
    translation.add_argument("--explanation", required=True)
    translation.add_argument("--confirmed", action="store_true")

    writing = sub.add_parser("add-writing")
    writing.add_argument("task_dir")
    writing.add_argument("--sentence", required=True)
    writing.add_argument("--meaning", required=True)
    writing.add_argument("--structure", required=True)
    writing.add_argument("--replaceable", required=True)
    writing.add_argument("--confirmed", action="store_true")

    args = parser.parse_args()
    task = Path(args.task_dir).resolve()
    if not task.is_dir():
        print(f"ERROR: 任务目录不存在：{task}", file=sys.stderr)
        return 1
    try:
        if args.command == "rebuild":
            result = rebuild(task)
        elif args.command == "status":
            result = status(task, args.terms)
        elif args.command == "add-vocab":
            result = add_vocab(task, args)
        elif args.command == "add-translation":
            result = add_translation(task, args)
        else:
            result = add_writing(task, args)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

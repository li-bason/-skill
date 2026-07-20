#!/usr/bin/env python3
"""End-to-end regression for the Markdown language accumulator."""

from __future__ import annotations

import tempfile
from argparse import Namespace
from pathlib import Path

from language_accumulator import (
    TRANSLATION_FILE,
    VOCAB_FILE,
    WRITING_FILE,
    add_translation,
    add_vocab,
    add_writing,
    parse_translations,
    parse_vocabulary,
    parse_writing,
    rebuild,
    status,
)


def args(**values):
    return Namespace(**values)


def main() -> int:
    errors = []
    with tempfile.TemporaryDirectory(prefix="fep-language-e2e-") as directory:
        task = Path(directory)
        (task / VOCAB_FILE).write_text("# 词汇语法积累表\n", encoding="utf-8")
        (task / TRANSLATION_FILE).write_text("# 翻译积累表\n", encoding="utf-8")
        (task / WRITING_FILE).write_text(
            "# 写作积累表\n\n| 英文句子 | 中文含义 | 句型结构 | 可替换部分 |\n"
            "| --- | --- | --- | --- |\n",
            encoding="utf-8",
        )
        try:
            add_vocab(task, args(
                term="contribute to", pos="phr v", definition="to help cause something",
                usage="contribute to + n / doing", example="Technology contributes to education.",
                synonyms="promote; help", confirmed=False,
            ))
            errors.append("未确认的词汇写入没有被拒绝")
        except ValueError:
            pass

        first = add_vocab(task, args(
            term="contribute to", pos="phr v", definition="to help cause something",
            usage="contribute to + n / doing", example="Technology contributes to education.",
            synonyms="promote; help", confirmed=True,
        ))
        second = add_vocab(task, args(
            term="Contribute   to", pos="phr v", definition="to give something to a shared purpose",
            usage="contribute sth to sth", example="She contributed an article to the magazine.",
            synonyms="donate; provide", confirmed=True,
        ))
        duplicate = add_vocab(task, args(
            term="contribute to", pos="phr v", definition="to help cause something",
            usage="contribute to + n / doing", example="Technology contributes to education.",
            synonyms="promote; help", confirmed=True,
        ))
        vocab = parse_vocabulary(task)
        if first["status"] != "added" or second["status"] != "added":
            errors.append("新词条或新义项没有成功写入")
        if duplicate["status"] != "duplicate":
            errors.append("重复义项没有被拦截")
        if len(vocab) != 1 or len(next(iter(vocab.values()))["senses"]) != 2:
            errors.append("同一词条没有合并为一个分组、两个义项")

        common_translation = dict(
            direction="英译中", sentence="Technology contributes to education.",
            segments="Technology / contributes to / education", translation="技术促进教育发展。",
            confirmed=True,
        )
        add_translation(task, args(
            **common_translation, expression="contribute to", explanation="表示促进。"
        ))
        add_translation(task, args(
            **common_translation, expression="education", explanation="表示教育。"
        ))
        translations = parse_translations(task)
        if len(translations) != 1 or len(next(iter(translations.values()))["expressions"]) != 2:
            errors.append("同一原句没有合并为一个分组、两个关键表达")

        writing_args = args(
            sentence="Technology can contribute to a better future.", meaning="科技可以促进更美好的未来。",
            structure="A can contribute to B", replaceable="Technology; a better future", confirmed=True,
        )
        add_writing(task, writing_args)
        writing_duplicate = add_writing(task, writing_args)
        if writing_duplicate["status"] != "duplicate" or len(parse_writing(task)) != 1:
            errors.append("重复写作句没有被拦截")

        rebuild(task)
        item = status(task, ["contribute to"])["terms"][0]
        if item["status"] != "已积累":
            errors.append("已积累状态识别失败")
        if len(item["translation_refs"]) != 1 or len(item["writing_refs"]) != 1:
            errors.append("三表跨表关联失败")

    for error in errors:
        print(f"ERROR: {error}")
    print("PASS" if not errors else "FAIL")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Select exact, directly relevant source sentences for one atomic point."""

from __future__ import annotations

import re

GENERIC = {
    "基本", "概念", "核心", "思想", "实现", "流程", "方法", "作用", "含义",
    "定义", "说明", "分析", "算法", "数据", "问题", "应用", "场景", "进行",
    "以及", "分别", "相关", "代表", "分类", "计算", "过程",
}
CORRUPT = re.compile(
    r"\?{2,}|\?[A-Za-z0-9]|[\u200b-\u200d]|[�]|Ø|NO!|分类任务训练数据"
)
OUTLINE_NOISE = re.compile(
    r"选择[、，,]?填空|填空[、，,]?判断|判断题|计算题|证明题|(?:^|\s)知识点(?:\s|$)|"
    r"第[一二三四五六七八九十]+章.{0,20}(?:知识点|选择|填空)"
)


def sentences(page_texts: list[str]) -> list[str]:
    text = "\n".join(page_texts)
    text = re.sub(r"(?m)^\s*\d+\s*$", "", text)
    # Preserve slide bullet boundaries before collapsing whitespace.  Extractors
    # commonly emit q/l/p/n/Ø/• as bullet glyphs.
    text = re.sub(r"(?m)^\s*(?:q|l|n|Ø|•|ü)\s+", "\n§ ", text)
    text = re.sub(r"(?m)^\s*p(?=\s|数据)", "\n§ ", text)
    text = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    parts = re.split(r"(?<=[。！？；])\s*|§\s*", text)
    result: list[str] = []
    for part in parts:
        part = re.sub(r"^[Øqlpn•ü]\s*", "", part.strip(" \t"))
        if len(part) < 8 or part in result:
            continue
        result.append(part)
    return result


def keywords(title: str, action: str) -> set[str]:
    text = re.sub(r"[A-Za-z0-9（）()、，,与及的和或]", " ", title + " " + action)
    words = {word for word in re.split(r"\s+", text) if len(word) >= 2}
    chunks = set(words)
    for word in words:
        for size in (2, 3, 4):
            chunks.update(word[i:i + size] for i in range(max(0, len(word) - size + 1)))
    return {word for word in chunks if word not in GENERIC}


def select(page_texts: list[str], title: str, action: str, limit: int = 6) -> list[str]:
    candidates = sentences(page_texts)
    keys = keywords(title, action)
    scored: list[tuple[int, int, str]] = []
    for index, sentence in enumerate(candidates):
        if CORRUPT.search(sentence) or OUTLINE_NOISE.search(sentence):
            continue
        score = sum(len(key) ** 2 for key in keys if key in sentence)
        if title in sentence:
            score += 30
        if any(mark in sentence for mark in ("定义", "目标", "是指", "称为", "步骤", "优点", "缺点", "表达式", "公式")):
            score += 4
        scored.append((score, -index, sentence))
    positive = [item for item in sorted(scored, reverse=True) if item[0] > 0]
    chosen = positive[:limit] or sorted(scored, reverse=True)[:2]
    chosen_sentences = {item[2] for item in chosen}
    result: list[str] = []
    for sentence in candidates:
        if sentence not in chosen_sentences:
            continue
        # Slide extraction often appends chart labels and full table contents to a
        # useful sentence. Keep the direct statement instead of the whole slide tail.
        if len(sentence) > 360:
            cut = sentence[:360]
            stops = [cut.rfind(mark) for mark in ("。", "；", "：")]
            stop = max(stops)
            sentence = cut[: stop + 1] if stop >= 80 else cut.rstrip() + "……"
        result.append(sentence)
        if sum(len(item) for item in result) >= 1100:
            break
    return result

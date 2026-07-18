#!/usr/bin/env python3
"""Normalize explicitly identified PDF symbol-font glyphs.

Unknown private-use characters remain unchanged so validation blocks delivery
instead of silently guessing their mathematical meaning.
"""

from __future__ import annotations

import argparse
from pathlib import Path


SYMBOL_MAP = str.maketrans({
    "": "¬", "": "∨", "": "∧", "": "⇔", "": "⇒",
    "": "↔", "": "∀", "": "∃", "": "Σ", "": "⊕",
    "": "∪", "": "•", "➢": "•", "": ":", "": ",",
})


def normalize_pdf_symbols(text: str) -> str:
    """Replace only glyphs whose meanings were verified from source context."""
    return text.translate(SYMBOL_MAP)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", help="UTF-8 text/Markdown files to repair in place")
    args = parser.parse_args()
    source_chars = tuple(chr(codepoint) for codepoint in SYMBOL_MAP)
    for value in args.paths:
        path = Path(value)
        before = path.read_text(encoding="utf-8")
        after = normalize_pdf_symbols(before)
        path.write_text(after, encoding="utf-8")
        count = sum(before.count(char) for char in source_chars)
        print(f"{path}: {count} replacement(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

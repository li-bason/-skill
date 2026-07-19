#!/usr/bin/env python3
"""Convert final-exam-prep Markdown artifacts to same-directory PDFs."""

from __future__ import annotations

import argparse
import base64
import html
import io
import re
import sys
from pathlib import Path

DELIVERABLES = {
    "知识点.md",
    "思维导图.md",
    "题目.md",
    "答案.md",
    "复习总结.md",
    "提纲.md",
    "新题答案.md",
}


def require_dependencies():
    try:
        import markdown  # noqa: F401
        import matplotlib  # noqa: F401
        import reportlab  # noqa: F401
    except ImportError as exc:
        raise RuntimeError(
            "缺少 PDF 依赖。请先执行：python -m pip install -r requirements.txt"
        ) from exc


def convert_reportlab(input_path: Path, output_path: Path, title: str) -> None:
    """Portable PDF fallback for Windows hosts without WeasyPrint native libraries."""
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4, A3, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import Image as RLImage
    from reportlab.platypus import Paragraph, Preformatted, SimpleDocTemplate, Spacer, Table, TableStyle

    page_size = landscape(A3) if input_path.stem == "思维导图" else A4

    font_path = Path(r"C:\Windows\Fonts\msyh.ttc")
    if not font_path.is_file():
        font_path = Path(r"C:\Windows\Fonts\simhei.ttf")
    pdfmetrics.registerFont(TTFont("CJK", str(font_path)))
    symbol_font_path = Path(r"C:\Windows\Fonts\seguisym.ttf")
    if symbol_font_path.is_file():
        pdfmetrics.registerFont(TTFont("MathSymbol", str(symbol_font_path)))
    styles = getSampleStyleSheet()
    body = ParagraphStyle("CJKBody", parent=styles["BodyText"], fontName="CJK", fontSize=9, leading=13.5, spaceAfter=4)
    h1 = ParagraphStyle("CJKH1", parent=body, fontSize=18, leading=24, alignment=TA_CENTER, spaceAfter=14)
    h2 = ParagraphStyle("CJKH2", parent=body, fontSize=14, leading=19, spaceBefore=10, spaceAfter=7, textColor=colors.HexColor("#17365D"))
    h3 = ParagraphStyle("CJKH3", parent=body, fontSize=11.5, leading=16, spaceBefore=8, spaceAfter=5, textColor=colors.HexColor("#244062"))
    h4 = ParagraphStyle("CJKH4", parent=body, fontSize=10.2, leading=14, spaceBefore=9, spaceAfter=3, textColor=colors.HexColor("#333333"))
    code = ParagraphStyle("CJKCode", parent=body, fontName="CJK", fontSize=7.8, leading=11, leftIndent=8, backColor=colors.HexColor("#F5F6F7"))
    option_style = ParagraphStyle("Option", parent=body, leftIndent=10, firstLineIndent=-10, spaceAfter=1)

    def inline(text: str) -> str:
        text = html.escape(text)
        text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
        text = re.sub(r"`(.+?)`", r"<font color='#8B1A1A'>\1</font>", text)
        if symbol_font_path.is_file():
            text = re.sub(
                r"([¬∧∨→↔⇒⇔∀∃∈∉⊆⊂∪∩⊕ΣΠ≤≥≠∞□⁻⁰¹²³⁴⁵⁶⁷⁸⁹₀₁₂₃₄₅₆₇₈₉])",
                r'<font name="MathSymbol">\1</font>',
                text,
            )
        return text

    raw_lines = input_path.read_text(encoding="utf-8").splitlines()
    story = []
    i = 0
    in_code = False
    code_lines: list[str] = []
    while i < len(raw_lines):
        line = raw_lines[i].rstrip()
        if line.startswith("```"):
            if in_code:
                story.extend([Preformatted("\n".join(code_lines), code), Spacer(1, 6)])
                code_lines = []
                in_code = False
            else:
                in_code = True
            i += 1
            continue
        if in_code:
            code_lines.append(line)
            i += 1
            continue
        if line.startswith("<!--"):
            i += 1
            continue
        image_match = re.fullmatch(r"!\[[^]]*\]\(([^)]+)\)", line.strip())
        if image_match:
            image_path = (input_path.parent / image_match.group(1)).resolve()
            if image_path.is_file():
                graphic = RLImage(str(image_path))
                available_w = page_size[0] - 3.2 * cm
                available_h = page_size[1] - 6.0 * cm
                scale = min(available_w / graphic.imageWidth, available_h / graphic.imageHeight)
                graphic.drawWidth = graphic.imageWidth * scale
                graphic.drawHeight = graphic.imageHeight * scale
                story.append(graphic)
            i += 1
            continue
        if line.startswith("|"):
            block: list[list[str]] = []
            while i < len(raw_lines) and raw_lines[i].lstrip().startswith("|"):
                cells = [cell.strip() for cell in raw_lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
                    block.append(cells)
                i += 1
            if block:
                cols = max(len(row) for row in block)
                data = [[Paragraph(inline(cell), body) for cell in row + [""] * (cols - len(row))] for row in block]
                width = (page_size[0] - 3.2 * cm) / cols
                table = Table(data, colWidths=[width] * cols, repeatRows=1)
                table.setStyle(TableStyle([
                    ("FONTNAME", (0, 0), (-1, -1), "CJK"), ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAF0F7")),
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#777777")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4), ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]))
                story.extend([table, Spacer(1, 7)])
            continue
        if not line or line == "---":
            previous = raw_lines[i - 1].strip() if i > 0 else ""
            following = raw_lines[i + 1].strip() if i + 1 < len(raw_lines) else ""
            compact = bool(re.match(r"^[ABCD][.．、:：]\s*", previous) or re.match(r"^[ABCD][.．、:：]\s*", following))
            story.append(Spacer(1, 1 if compact else 5))
        elif line.startswith("#### "):
            story.append(Paragraph(inline(line[5:]), h4))
        elif line.startswith("### "):
            story.append(Paragraph(inline(line[4:]), h3))
        elif line.startswith("## "):
            story.append(Paragraph(inline(line[3:]), h2))
        elif line.startswith("# "):
            story.append(Paragraph(inline(line[2:]), h1))
        elif line.startswith("> "):
            story.append(Paragraph(inline(line[2:]), ParagraphStyle("Quote", parent=body, leftIndent=12, textColor=colors.HexColor("#555555"))))
        elif re.match(r"^\d+\.\s", line):
            story.append(Paragraph(inline(line), ParagraphStyle("Number", parent=body, leftIndent=12, firstLineIndent=-10)))
        elif line.startswith(('- ', '* ')):
            story.append(Paragraph("• " + inline(line[2:]), ParagraphStyle("Bullet", parent=body, leftIndent=12, firstLineIndent=-8)))
        elif re.match(r"^[ABCD][.．、:：]\s*", line):
            story.append(Paragraph(inline(line), option_style))
        else:
            story.append(Paragraph(inline(line), body))
        i += 1

    def footer(canvas, document):
        canvas.saveState()
        canvas.setFont("CJK", 8)
        canvas.setFillColor(colors.HexColor("#666666"))
        canvas.drawCentredString(page_size[0] / 2, 0.75 * cm, f"{title}  ·  {document.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(str(output_path), pagesize=page_size, leftMargin=1.6 * cm, rightMargin=1.6 * cm, topMargin=1.6 * cm, bottomMargin=1.25 * cm, title=title)
    doc.build(story, onFirstPage=footer, onLaterPages=footer)


def render_math_svg(expression: str, display: bool) -> str | None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure = plt.figure(figsize=(0.01, 0.01))
    figure.patch.set_alpha(0)
    try:
        figure.text(
            0.5,
            0.5,
            f"${expression.strip()}$",
            fontsize=14 if display else 11,
            ha="center",
            va="center",
            usetex=False,
        )
        buffer = io.BytesIO()
        figure.savefig(
            buffer,
            format="svg",
            bbox_inches="tight",
            pad_inches=0.05,
            transparent=True,
        )
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        return f"data:image/svg+xml;base64,{encoded}"
    except Exception as exc:  # matplotlib mathtext supports only a LaTeX subset
        print(f"[md-to-pdf] WARN: 公式渲染失败：{exc}", file=sys.stderr)
        return None
    finally:
        plt.close(figure)


def process_math(markdown_text: str) -> str:
    placeholders: dict[str, tuple[str, bool]] = {}

    def stash(match: re.Match[str], display: bool) -> str:
        key = f"MATHPLACEHOLDER{len(placeholders)}TOKEN"
        placeholders[key] = (match.group(1), display)
        return key

    text = re.sub(r"\$\$(.+?)\$\$", lambda m: stash(m, True), markdown_text, flags=re.S)
    text = re.sub(
        r"(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)",
        lambda m: stash(m, False),
        text,
    )
    for key, (expression, display) in placeholders.items():
        uri = render_math_svg(expression, display)
        escaped = html.escape(expression)
        if uri:
            replacement = (
                f'<div class="math-display"><img src="{uri}" alt="{escaped}"></div>'
                if display
                else f'<span class="math-inline"><img src="{uri}" alt="{escaped}"></span>'
            )
        else:
            delimiter = "$$" if display else "$"
            replacement = f"`{delimiter}{expression}{delimiter}`"
        text = text.replace(key, replacement)
    return text


def css(title: str) -> str:
    safe_header = title.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
    return f"""
@page {{
  size: A4;
  margin: 2.2cm 1.8cm;
  @top-center {{ content: \"{safe_header}\"; font-size: 9pt; color: #666; }}
  @bottom-center {{ content: counter(page); font-size: 9pt; color: #666; }}
}}
body {{ font-family: \"Cambria Math\", \"Segoe UI Symbol\", \"Noto Sans CJK SC\", \"Microsoft YaHei\", SimSun, sans-serif; font-size: 11pt; line-height: 1.65; color: #222; }}
h1 {{ font-size: 21pt; text-align: center; margin: 1cm 0 .6cm; }}
h2 {{ font-size: 16pt; border-bottom: 1px solid #bbb; padding-bottom: 4pt; margin-top: .8cm; }}
h3 {{ font-size: 13pt; margin-top: .6cm; }}
p {{ margin: .25cm 0; }}
table {{ border-collapse: collapse; width: 100%; margin: .4cm 0; font-size: 9.5pt; }}
th, td {{ border: 1px solid #555; padding: 6pt; vertical-align: top; }}
th {{ background: #f1f3f5; }}
pre {{ white-space: pre-wrap; overflow-wrap: anywhere; border: 1px solid #ddd; border-left: 3px solid #4a78c2; background: #f8f9fa; padding: 9pt; page-break-inside: avoid; }}
code {{ font-family: \"Segoe UI Symbol\", \"Cambria Math\", \"Microsoft YaHei\", \"Noto Sans Symbols 2\", sans-serif; font-size: 9pt; }}
blockquote {{ border-left: 3px solid #4a78c2; margin: .35cm 0; padding: .15cm .6cm; background: #f8f9fa; }}
img {{ max-width: 100%; height: auto; }}
.math-display {{ text-align: center; margin: .35cm 0; page-break-inside: avoid; }}
.math-inline {{ display: inline-block; vertical-align: middle; }}
.math-inline img {{ height: 1.25em; vertical-align: middle; }}
li {{ margin: .08cm 0; }}
"""


def markdown_to_html(markdown_text: str, title: str) -> str:
    import markdown

    processed = process_math(markdown_text)
    body = markdown.markdown(
        processed,
        extensions=["extra", "fenced_code", "sane_lists", "tables"],
        output_format="html5",
    )
    return (
        "<!doctype html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">"
        f"<title>{html.escape(title)}</title><style>{css(title)}</style></head>"
        f"<body>{body}</body></html>"
    )


def convert(input_path: Path, output_path: Path | None = None, title: str | None = None) -> Path:
    require_dependencies()
    input_path = input_path.resolve()
    if not input_path.is_file() or input_path.suffix.lower() != ".md":
        raise ValueError(f"输入必须是存在的 Markdown 文件：{input_path}")
    output_path = (output_path or input_path.with_suffix(".pdf")).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    document_title = title or input_path.stem
    try:
        from weasyprint import HTML
        source = input_path.read_text(encoding="utf-8")
        rendered = markdown_to_html(source, document_title)
        HTML(string=rendered, base_url=str(input_path.parent)).write_pdf(str(output_path))
    except (ImportError, OSError):
        convert_reportlab(input_path, output_path, document_title)
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", help="Markdown 文件")
    parser.add_argument("--output", help="输出 PDF 路径；默认与输入同目录同名")
    parser.add_argument("--title", help="PDF 标题")
    parser.add_argument("--all", dest="directory", help="批量转换任务目录中的正式产物")
    args = parser.parse_args()

    try:
        if args.directory:
            directory = Path(args.directory).resolve()
            if not directory.is_dir():
                raise ValueError(f"目录不存在：{directory}")
            inputs = [directory / name for name in sorted(DELIVERABLES) if (directory / name).is_file()]
            if not inputs:
                raise ValueError("目录中没有可转换的正式 Markdown 产物")
            outputs = [convert(path) for path in inputs]
        elif args.input:
            outputs = [convert(Path(args.input), Path(args.output) if args.output else None, args.title)]
        else:
            parser.error("请提供 input 或 --all DIRECTORY")
            return 2
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"[md-to-pdf] ERROR: {exc}", file=sys.stderr)
        return 1

    for output in outputs:
        print(f"[md-to-pdf] OK: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

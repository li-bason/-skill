#!/usr/bin/env python3
"""Render an atomic-point map as a local, immediately viewable PNG mind map."""

from __future__ import annotations

import argparse
import json
import textwrap
from collections import OrderedDict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    names = ["msyhbd.ttc" if bold else "msyh.ttc", "simhei.ttf", "simsun.ttc"]
    for name in names:
        path = Path("C:/Windows/Fonts") / name
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def rounded(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], fill: str, outline: str, width: int = 3) -> None:
    draw.rounded_rectangle(box, radius=18, fill=fill, outline=outline, width=width)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task_dir")
    parser.add_argument("map_file")
    args = parser.parse_args()
    task = Path(args.task_dir)
    atoms = json.loads(Path(args.map_file).read_text(encoding="utf-8"))["atoms"]
    manifest = json.loads((task / "source_manifest.json").read_text(encoding="utf-8"))
    task_name = manifest.get("task", "课程")

    groups: OrderedDict[str, list[dict]] = OrderedDict()
    for atom in atoms:
        groups.setdefault(atom.get("parent", "未分组"), []).append(atom)

    row_h, gap, top = 92, 22, 100
    group_gap = 34
    height = top * 2 + sum(len(items) * (row_h + gap) + group_gap for items in groups.values())
    width = 3200
    image = Image.new("RGB", (width, height), "#F7F9FC")
    draw = ImageDraw.Draw(image)
    title_font, root_font = font(52, True), font(34, True)
    group_font, atom_font, id_font = font(29, True), font(25), font(22, True)

    draw.text((90, 28), f"{task_name}期末复习思维导图", font=title_font, fill="#172033")
    root_box = (90, height // 2 - 95, 600, height // 2 + 95)
    rounded(draw, root_box, "#275DAD", "#1D4787", 5)
    root_lines = textwrap.wrap(f"{task_name}\n期末复习", width=12)
    y = height // 2 - len(root_lines) * 25
    for line in root_lines:
        box = draw.textbbox((0, 0), line, font=root_font)
        draw.text(((root_box[0] + root_box[2] - (box[2] - box[0])) / 2, y), line, font=root_font, fill="white")
        y += 50

    group_x1, group_x2 = 850, 1510
    atom_x1, atom_x2 = 1780, 3110
    cursor = top
    palette = [("#E8F1FF", "#3973C5"), ("#EAF7F1", "#318A63"), ("#FFF3E6", "#C9782D"), ("#F3ECFF", "#7652B7")]
    centers = []
    for group_index, (parent, items) in enumerate(groups.items()):
        block_h = len(items) * (row_h + gap) - gap
        group_center = cursor + block_h // 2
        centers.append(group_center)
        fill, stroke = palette[group_index % len(palette)]
        group_box = (group_x1, group_center - 54, group_x2, group_center + 54)
        rounded(draw, group_box, fill, stroke)
        label = parent if len(parent) <= 19 else parent[:18] + "…"
        bbox = draw.textbbox((0, 0), label, font=group_font)
        draw.text((group_x1 + 28, group_center - (bbox[3] - bbox[1]) / 2 - 3), label, font=group_font, fill="#172033")
        draw.line((root_box[2], height // 2, group_x1, group_center), fill="#9BAAC0", width=4)

        for item_index, atom in enumerate(items):
            cy = cursor + item_index * (row_h + gap) + row_h // 2
            draw.line((group_x2, group_center, atom_x1, cy), fill=stroke, width=3)
            atom_box = (atom_x1, cy - row_h // 2, atom_x2, cy + row_h // 2)
            rounded(draw, atom_box, "#FFFFFF", "#CBD5E1", 2)
            draw.text((atom_x1 + 24, cy - 18), atom["id"], font=id_font, fill=stroke)
            title = atom["title"] if len(atom["title"]) <= 38 else atom["title"][:37] + "…"
            draw.text((atom_x1 + 165, cy - 20), title, font=atom_font, fill="#253047")
        cursor += block_h + group_gap

    image.save(task / "思维导图.png", optimize=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

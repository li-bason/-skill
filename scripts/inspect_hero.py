#!/usr/bin/env python3
"""Create a contact sheet of representative hero GIF frames for visual QA."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
import importlib.util

root = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("hero_renderer", root / "scripts" / "render_readme_hero.py")
renderer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(renderer)
times = [0.8, 2.1, 4.5, 6.7, 9.2, 11.6, 13.2, 15.2]
thumbs = []
for seconds in times:
    frame = renderer.frame_at(seconds).convert("RGB").resize((480, 270))
    draw = ImageDraw.Draw(frame)
    draw.rectangle((0, 0, 70, 26), fill="#191714")
    draw.text((8, 5), f"{seconds:.1f}s", fill="white", font=ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 13))
    thumbs.append(frame)

sheet = Image.new("RGB", (960, 1080), "#D8D2C8")
for i, frame in enumerate(thumbs):
    sheet.paste(frame, ((i % 2) * 480, (i // 2) * 270))
sheet.save(root / "assets" / "hero-contact-sheet.png")

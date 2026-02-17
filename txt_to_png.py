#!/usr/bin/env python3
"""Render a text file (pre-rendered terminal output) to a PNG image.

Usage: python3 txt_to_png.py input.txt output.png
Requires: Pillow (pip install pillow)
"""
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except Exception:
    print("Pillow is required. Install with: pip install pillow", file=sys.stderr)
    raise


def render_text_file_to_png(input_path, output_path, font_path=None, font_size=14, padding=8, bg=(255,255,255), fg=(0,0,0)):
    text = Path(input_path).read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines() or [""]

    if font_path is None:
        # try common monospace font on Linux
        possible = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
        ]
        for p in possible:
            p = Path(p)
            if p.exists():
                font_path = str(p)
                break

    if font_path:
        try:
            font = ImageFont.truetype(font_path, font_size)
        except Exception:
            font = ImageFont.load_default()
    else:
        font = ImageFont.load_default()

    # measure
    # measure using a temporary ImageDraw for compatibility
    max_width = 0
    line_height = 0
    for ln in lines:
        try:
            mask = font.getmask(ln)
            w, h = mask.size
        except Exception:
            # fallback
            w, h = font.getsize(ln)
        if w > max_width:
            max_width = w
        line_height = max(line_height, h)

    img_w = max_width + padding * 2
    img_h = line_height * len(lines) + padding * 2

    img = Image.new("RGB", (img_w, img_h), color=bg)
    draw = ImageDraw.Draw(img)

    y = padding
    for ln in lines:
        draw.text((padding, y), ln, font=font, fill=fg)
        y += line_height

    img.save(output_path)


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 txt_to_png.py input.txt output.png", file=sys.stderr)
        sys.exit(2)
    inp = sys.argv[1]
    out = sys.argv[2]
    render_text_file_to_png(inp, out)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()

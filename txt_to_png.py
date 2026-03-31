#!/usr/bin/env python3
"""Render a text file (pre-rendered terminal output) to a PNG image.
Supports reverse-video markup: text wrapped in [...] is rendered with
a highlighted background (yellow bg, black text).

Usage: python3 txt_to_png.py input.txt output.png
Requires: Pillow (pip install pillow)
"""
import sys
import re
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except Exception:
    print("Pillow is required. Install with: pip install pillow", file=sys.stderr)
    raise

# Colour scheme
BG_NORMAL  = (20,  20,  20)   # dark background
FG_NORMAL  = (200, 200, 200)  # light grey text
BG_REVERSE = (220, 200,  0)   # yellow highlight
FG_REVERSE = (0,   0,   0)    # black text on highlight


def _parse_spans(line: str):
    """
    Parse a line that may contain [...] reverse-video markers.
    Returns list of (text, reverse) tuples.
    Nested brackets not supported; unmatched [ treated as literal.
    """
    spans = []
    i = 0
    while i < len(line):
        bracket = line.find("[", i)
        if bracket == -1:
            spans.append((line[i:], False))
            break
        if bracket > i:
            spans.append((line[i:bracket], False))
        close = line.find("]", bracket + 1)
        if close == -1:
            # no closing bracket — treat rest as normal
            spans.append((line[bracket:], False))
            break
        inner = line[bracket + 1:close]
        spans.append((inner, True))
        i = close + 1
    return spans if spans else [("", False)]


def _load_font(font_size=14):
    possible = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
    ]
    for p in possible:
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, font_size)
            except Exception:
                pass
    return ImageFont.load_default()


def _char_size(font, font_size, line_spacing=6):
    """Return (char_width, line_height) for a monospace font. line_spacing adds extra vertical padding."""
    # Measure a long string and divide — more accurate than single-char bbox
    test = "M" * 40
    try:
        bbox = font.getbbox(test)
        char_w = (bbox[2] - bbox[0]) / 40
        bbox1 = font.getbbox("M")
        line_h = bbox1[3] - bbox1[1] + 2 + line_spacing
        return char_w, line_h
    except Exception:
        try:
            w, h = font.getsize(test)
            return w / 40, h + 2 + line_spacing
        except Exception:
            return font_size / 2, font_size + 2 + line_spacing


def render_text_file_to_png(input_path, output_path, font_path=None, font_size=14,
                             padding=8, bg=None, fg=None):
    """
    Render input_path (text with optional [...] reverse markers) to output_path PNG.
    bg/fg kept for API compatibility but ignored (dark theme used instead).
    """
    text  = Path(input_path).read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines() or [""]

    font      = ImageFont.truetype(font_path, font_size) if font_path and Path(font_path).exists() \
                else _load_font(font_size)
    char_w, line_h = _char_size(font, font_size, line_spacing=6)

    # measure max width in chars
    max_chars = max((len(ln) for ln in lines), default=0)
    img_w = round(max_chars * char_w) + padding * 2
    img_h = line_h * len(lines) + padding * 2

    img  = Image.new("RGB", (img_w, img_h), color=BG_NORMAL)
    draw = ImageDraw.Draw(img)

    # Build a lookup: pixel x start for column n = round(n * char_w)
    # But to avoid drift, precompute all col->x offsets using the font's
    # actual per-glyph advance for a reference string of spaces.
    # Simplest accurate approach: draw each span at x = padding + round(col * char_w)
    # and draw the background rect from x0 to x0 + measured span width.
    y = padding
    for ln in lines:
        spans = _parse_spans(ln)
        col = 0
        for text_seg, reverse in spans:
            if not text_seg:
                continue
            x0 = padding + round(col * char_w)
            # Measure exact pixel width of this segment using the font
            try:
                seg_px = round(font.getlength(text_seg))
            except AttributeError:
                try:
                    seg_px = font.getbbox(text_seg)[2] - font.getbbox(text_seg)[0]
                except Exception:
                    seg_px = round(len(text_seg) * char_w)
            if reverse:
                draw.rectangle([x0, y, x0 + seg_px, y + line_h - 1], fill=BG_REVERSE)
                draw.text((x0, y), text_seg, font=font, fill=FG_REVERSE)
            else:
                draw.text((x0, y), text_seg, font=font, fill=FG_NORMAL)
            col += len(text_seg)
        y += line_h

    img.save(output_path)


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 txt_to_png.py input.txt output.png", file=sys.stderr)
        sys.exit(2)
    render_text_file_to_png(sys.argv[1], sys.argv[2])
    print(f"Wrote {sys.argv[2]}")


if __name__ == "__main__":
    main()

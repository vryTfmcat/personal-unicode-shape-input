"""Draw small, high-contrast Weasel status icons from geometric primitives."""
from __future__ import annotations
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

MODE_LABELS = {0: "候选层关闭", 1: "区块", 2: "全形", 3: "区块＋全形",
               4: "收藏", 5: "区块＋收藏", 6: "全形＋收藏", 7: "三者混合"}
COLORS = {1: "#75BFFF", 2: "#63E4C2", 4: "#FFD175"}
SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256)


def schema_id(mask: int) -> str:
    return "personal_unicode_modes" if mask == 1 else f"personal_unicode_modes_{mask}"


def icon(mask: int | str, size: int) -> Image.Image:
    # Supersampling retains the same proportions at every taskbar DPI.
    scale = size * 4 / 32
    im = Image.new("RGBA", (size * 4, size * 4))
    d = ImageDraw.Draw(im)
    def box(x): return tuple(round(v * scale) for v in x)
    def line(points, color, width=2):
        d.line([tuple(round(v * scale) for v in p) for p in points], fill=color,
               width=max(1, round(width * scale)), joint="curve")
    d.rounded_rectangle(box((1, 1, 31, 31)), radius=round(6 * scale),
                        fill="#18232E", outline="#D5DFE9", width=max(1, round(scale)))
    if mask == 1:
        for x in (7, 18):
            for y in (7, 18):
                d.rounded_rectangle(box((x, y, x + 7, y + 7)), radius=round(1.5 * scale), fill=COLORS[1])
    elif mask == 2:
        d.ellipse(box((6, 6, 22, 22)), outline=COLORS[2], width=round(3 * scale))
        d.polygon([box(p) for p in ((23, 16), (29, 26), (17, 26))], fill=COLORS[2])
    elif mask == 4:
        points=[]
        for i in range(10):
            a = -math.pi / 2 + i * math.pi / 5
            r = 11.5 if i % 2 == 0 else 5.2
            points.append(box((16 + math.cos(a) * r, 16 + math.sin(a) * r)))
        d.polygon(points, fill=COLORS[4])
    elif mask == "ascii":
        line([(7, 25), (16, 7), (25, 25)], "#F3F7FC", 3)
        line([(11, 19), (21, 19)], "#F3F7FC", 3)
    elif mask == 0:
        d.ellipse(box((7, 7, 25, 25)), outline="#A6B4C3", width=round(2.5 * scale))
        line([(9, 23), (23, 9)], "#A6B4C3", 2.5)
    else:
        active = [bit for bit in (1, 2, 4) if mask & bit]
        for i, bit in enumerate(active):
            x = 5 + i * 4; y = 5 + i * 4
            d.rounded_rectangle(box((x, y, x + 14, y + 12)), radius=round(2 * scale),
                                fill=COLORS[bit], outline="#18232E", width=round(scale))
        # Fixed blue / green / amber positions reveal which layers are enabled.
        for x, bit in zip((8, 16, 24), (1, 2, 4)):
            d.ellipse(box((x - 2, 26, x + 2, 30)), fill=COLORS[bit] if mask & bit else "#536171")
    return im.resize((size, size), Image.Resampling.LANCZOS)


def write_icons(output: Path):
    output.mkdir(parents=True, exist_ok=True)
    for mask in (*range(8), "ascii"):
        # Independent raster sizes avoid blur from Windows scaling a single bitmap.
        pictures = [icon(mask, size) for size in SIZES]
        pictures[-1].save(output / f"unicode_mode_{mask}.ico", format="ICO",
                          sizes=[(s, s) for s in SIZES], append_images=pictures[:-1])


def preview(path: Path):
    im = Image.new("RGB", (760, 330), "#111A24")
    d = ImageDraw.Draw(im)
    font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 20)
    for i, mask in enumerate((1, 2, 4, 7, 3, 5, 6, "ascii")):
        x, y = 35 + (i % 4) * 188, 24 + (i // 4) * 150
        picture = icon(mask, 64); im.paste(picture, (x + 42, y), picture)
        label = "英文" if mask == "ascii" else MODE_LABELS[mask]
        d.text((x + 74, y + 72), label, fill="#F3F7FC", font=font, anchor="mt")
        for j, size in enumerate((16, 24, 32)):
            picture = icon(mask, size); im.paste(picture, (x + 26 + j * 37, y + 108), picture)
    path.parent.mkdir(parents=True, exist_ok=True); im.save(path)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MARD 221 printable bead pattern generator.

Reads an image, scales it to a bead grid, maps each bead to nearest MARD 221
RGB color, and exports:
  <prefix>.pdf
  <prefix>_page1.png
  <prefix>_preview.png
  <prefix>_counts.csv

Default behavior treats white backgrounds as beads. Use --blank-white only when
explicitly creating an empty/省豆/去白底 version.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps, ImageStat, JpegImagePlugin  # noqa: F401

RGB = Tuple[int, int, int]
GridCell = Optional[str]

def default_palette_path() -> Path:
    """Find the installed MARD 221 palette across Hermes profile/home layouts."""
    candidates = []
    env = os.environ.get("MARD221_PALETTE")
    if env:
        candidates.append(Path(env).expanduser())
    candidates.extend([
        Path.home() / ".hermes" / "data" / "mard221_palette.json",
        Path(__file__).resolve().parents[1] / "data" / "mard221_palette.json",
        Path("/home/ubuntu/.hermes/data/mard221_palette.json"),
    ])
    for p in candidates:
        if p.exists():
            return p
    return candidates[0] if candidates else Path("mard221_palette.json")


DEFAULT_PALETTE = default_palette_path()


def parse_size(value: str) -> Tuple[int, int]:
    m = re.match(r"^\s*(\d+)\s*[xX×*，,]\s*(\d+)\s*$", value or "")
    if not m:
        raise argparse.ArgumentTypeError("size must look like 80x80 or 40x60")
    w, h = int(m.group(1)), int(m.group(2))
    if w <= 0 or h <= 0 or w > 300 or h > 300:
        raise argparse.ArgumentTypeError("size must be in 1..300 for both dimensions")
    return w, h


def load_palette(path: Path) -> List[Dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    colors = data.get("colors") or data.get("palette") or (data if isinstance(data, list) else [])
    out = []
    for c in colors:
        tag = str(c["tag"]).upper().strip()
        hx = str(c.get("hex") or "").upper().strip()
        rgb = c.get("rgb")
        if not rgb and re.match(r"^#[0-9A-F]{6}$", hx):
            rgb = [int(hx[i:i+2], 16) for i in (1, 3, 5)]
        if len(rgb) != 3:
            raise ValueError(f"bad RGB for {tag}")
        if not hx:
            hx = "#%02X%02X%02X" % tuple(rgb)
        out.append({"tag": tag, "hex": hx, "rgb": tuple(int(v) for v in rgb)})
    if len(out) != 221:
        raise ValueError(f"palette must contain 221 colors, got {len(out)} from {path}")
    if len({c["tag"] for c in out}) != 221:
        raise ValueError("palette has duplicate tags")
    return out


def find_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = []
    if bold:
        candidates += [
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJKsc-Bold.otf",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]
    candidates += [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/truetype/arphic/uming.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size=size)
            except Exception:
                pass
    return ImageFont.load_default()


def text_size(draw: ImageDraw.ImageDraw, text: str, font) -> Tuple[int, int]:
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0], box[3] - box[1]


def fit_text(draw: ImageDraw.ImageDraw, text: str, max_w: int, font_path_size: int = 18, bold: bool = False):
    for sz in range(font_path_size, 6, -1):
        f = find_font(sz, bold=bold)
        if text_size(draw, text, f)[0] <= max_w:
            return f
    return find_font(7, bold=bold)


def analyze_complexity(img: Image.Image) -> Tuple[str, int, Dict[str, float]]:
    """Return complexity label, recommended long side, metrics."""
    small = ImageOps.exif_transpose(img).convert("RGB")
    small.thumbnail((160, 160), Image.Resampling.LANCZOS)
    # Edge-ish metric from FIND_EDGES grayscale.
    gray = ImageOps.grayscale(small)
    edge = gray.filter(ImageFilter.FIND_EDGES)
    edge_mean = ImageStat.Stat(edge).mean[0] / 255.0
    # Color variety after posterization.
    quant = small.quantize(colors=96, method=Image.Quantize.MEDIANCUT)
    hist = quant.histogram()
    used = sum(1 for v in hist if v)
    variety = min(1.0, used / 96.0)
    # Entropy-ish brightness spread.
    entropy = gray.entropy() / 8.0
    score = 0.45 * edge_mean + 0.35 * variety + 0.20 * entropy
    # Ranges requested by user: simple 40-60, normal 50-70, anime 70-90,
    # complex people 90-120. This heuristic chooses a conservative printable size.
    if score < 0.34:
        label, long_side = "简单图", 50
    elif score < 0.50:
        label, long_side = "普通角色/图案", 64
    elif score < 0.66:
        label, long_side = "动漫头像/半身", 82
    else:
        label, long_side = "复杂人物/高细节", 104
    return label, long_side, {"edge": edge_mean, "variety": variety, "entropy": entropy, "score": score}


def target_dimensions(img: Image.Image, args) -> Tuple[int, int, str, Dict[str, float]]:
    iw, ih = ImageOps.exif_transpose(img).size
    if args.size:
        return args.size[0], args.size[1], "用户指定尺寸", {}
    if args.width and args.height:
        return args.width, args.height, "用户指定尺寸", {}
    if args.width:
        h = max(1, round(args.width * ih / iw))
        return args.width, h, "用户指定宽度，保持比例", {}
    if args.height:
        w = max(1, round(args.height * iw / ih))
        return w, args.height, "用户指定高度，保持比例", {}
    label, long_side, metrics = analyze_complexity(img)
    if args.long_side:
        long_side = args.long_side
        label = "用户指定长边，保持比例"
    if iw >= ih:
        w = long_side
        h = max(1, round(long_side * ih / iw))
    else:
        h = long_side
        w = max(1, round(long_side * iw / ih))
    return w, h, label, metrics


def composite_to_rgb(img: Image.Image) -> Image.Image:
    img = ImageOps.exif_transpose(img)
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        rgba = img.convert("RGBA")
        bg = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        return Image.alpha_composite(bg, rgba).convert("RGB")
    return img.convert("RGB")


def nearest_color(rgb: RGB, palette: Sequence[Dict]) -> Dict:
    r, g, b = rgb
    best = None
    best_d = 10**9
    # Slightly weighted perceptual-ish RGB distance.
    for c in palette:
        cr, cg, cb = c["rgb"]
        dr, dg, db = r - cr, g - cg, b - cb
        d = 2 * dr * dr + 4 * dg * dg + 3 * db * db
        if d < best_d:
            best_d = d
            best = c
    return best


def map_image(img: Image.Image, w: int, h: int, palette: Sequence[Dict], blank_white: bool = False, blank_threshold: int = 245):
    src = ImageOps.exif_transpose(img)
    alpha = None
    if src.mode in ("RGBA", "LA") or (src.mode == "P" and "transparency" in src.info):
        rgba = src.convert("RGBA").resize((w, h), Image.Resampling.LANCZOS)
        alpha = rgba.getchannel("A")
        rgb_img = composite_to_rgb(src).resize((w, h), Image.Resampling.LANCZOS)
    else:
        rgb_img = src.convert("RGB").resize((w, h), Image.Resampling.LANCZOS)
    tag_to_color = {c["tag"]: c for c in palette}
    grid: List[List[GridCell]] = []
    counts: Counter[str] = Counter()
    pixels = rgb_img.load()
    for y in range(h):
        row = []
        for x in range(w):
            r, g, b = pixels[x, y]
            is_blank = False
            if blank_white and r >= blank_threshold and g >= blank_threshold and b >= blank_threshold:
                is_blank = True
            if blank_white and alpha is not None and alpha.getpixel((x, y)) < 128:
                is_blank = True
            if is_blank:
                row.append(None)
            else:
                c = nearest_color((r, g, b), palette)
                row.append(c["tag"])
                counts[c["tag"]] += 1
        grid.append(row)
    return grid, counts, tag_to_color, rgb_img


def make_preview(grid, tag_to_color, scale: int = 10) -> Image.Image:
    h, w = len(grid), len(grid[0])
    img = Image.new("RGB", (w * scale, h * scale), "white")
    d = ImageDraw.Draw(img)
    for y, row in enumerate(grid):
        for x, tag in enumerate(row):
            if tag is None:
                fill = (255, 255, 255)
            else:
                fill = tag_to_color[tag]["rgb"]
            d.rectangle([x * scale, y * scale, (x + 1) * scale - 1, (y + 1) * scale - 1], fill=fill)
    return img


def draw_overview_grid(grid, tag_to_color, max_w: int, max_h: int, show_text: bool = False) -> Image.Image:
    h, w = len(grid), len(grid[0])
    cell = max(2, min(max_w // w, max_h // h))
    img = Image.new("RGB", (w * cell + 1, h * cell + 1), "white")
    d = ImageDraw.Draw(img)
    font = find_font(max(6, min(12, cell - 2)))
    for y, row in enumerate(grid):
        for x, tag in enumerate(row):
            x0, y0 = x * cell, y * cell
            fill = (255, 255, 255) if tag is None else tag_to_color[tag]["rgb"]
            d.rectangle([x0, y0, x0 + cell, y0 + cell], fill=fill)
            if cell >= 14 and show_text and tag:
                tw, th = text_size(d, tag, font)
                lum = sum(fill) / 3
                d.text((x0 + (cell - tw) / 2, y0 + (cell - th) / 2 - 1), tag, font=font, fill=(0, 0, 0) if lum > 130 else (255, 255, 255))
    for x in range(w + 1):
        lw = 2 if x % 10 == 0 else (1 if x % 5 == 0 else 1)
        col = (70, 70, 70) if x % 10 == 0 else ((120, 120, 120) if x % 5 == 0 else (210, 210, 210))
        d.line([(x * cell, 0), (x * cell, h * cell)], fill=col, width=lw)
    for y in range(h + 1):
        lw = 2 if y % 10 == 0 else (1 if y % 5 == 0 else 1)
        col = (70, 70, 70) if y % 10 == 0 else ((120, 120, 120) if y % 5 == 0 else (210, 210, 210))
        d.line([(0, y * cell), (w * cell, y * cell)], fill=col, width=lw)
    return img


def paste_fit(page: Image.Image, img: Image.Image, box: Tuple[int, int, int, int], bg=(255, 255, 255)):
    x0, y0, x1, y1 = box
    canvas = Image.new("RGB", (x1 - x0, y1 - y0), bg)
    im = img.convert("RGB").copy()
    im.thumbnail((x1 - x0, y1 - y0), Image.Resampling.LANCZOS)
    canvas.paste(im, ((canvas.width - im.width) // 2, (canvas.height - im.height) // 2))
    page.paste(canvas, (x0, y0))


def draw_color_list(d: ImageDraw.ImageDraw, counts: Counter, tag_to_color: Dict[str, Dict], x: int, y: int, w: int, h: int, font, small_font):
    total_colors = len(counts)
    row_h = 24 if total_colors <= 28 else max(15, min(22, h // max(total_colors, 1)))
    d.text((x, y), "颜色清单 / 用量", font=font, fill=(0, 0, 0))
    yy = y + 34
    headers = "色号  色块    HEX      数量"
    d.text((x, yy), headers, font=small_font, fill=(80, 80, 80))
    yy += row_h
    for tag, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        c = tag_to_color[tag]
        if yy + row_h > y + h:
            d.text((x, yy), f"…另 {total_colors} 色详见CSV", font=small_font, fill=(150, 0, 0))
            break
        d.rectangle([x + 45, yy + 2, x + 72, yy + row_h - 3], fill=c["rgb"], outline=(80, 80, 80))
        d.text((x, yy), f"{tag:<4}", font=small_font, fill=(0, 0, 0))
        d.text((x + 82, yy), f"{c['hex']}  {n}", font=small_font, fill=(0, 0, 0))
        yy += row_h


def make_cover_page(title: str, original: Image.Image, preview: Image.Image, grid, counts: Counter, tag_to_color, dimension_note: str, metrics: Dict[str, float], blank_white: bool) -> Image.Image:
    W, H = 1240, 1754  # A4-ish at 150dpi
    page = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(page)
    title_font = find_font(40, bold=True)
    h1 = find_font(26, bold=True)
    body = find_font(20)
    small = find_font(16)
    tiny = find_font(13)
    margin = 58
    d.text((margin, 42), title, font=title_font, fill=(0, 0, 0))
    gw, gh = len(grid[0]), len(grid)
    total = sum(counts.values())
    meta = f"尺寸：{gw}×{gh} 格｜总格数：{gw*gh}｜用豆数：{total}｜颜色数：{len(counts)}｜{dimension_note}"
    d.text((margin, 100), meta, font=body, fill=(35, 35, 35))
    if metrics:
        d.text((margin, 130), "复杂度指标：score={score:.2f}, edge={edge:.2f}, variety={variety:.2f}".format(**metrics), font=small, fill=(100, 100, 100))

    # Panels
    panel_top = 172
    left_w = 720
    right_x = margin + left_w + 38
    d.rounded_rectangle([margin, panel_top, margin + 335, panel_top + 320], radius=12, outline=(220, 220, 220), width=2)
    d.text((margin + 18, panel_top + 14), "原图", font=h1, fill=(0, 0, 0))
    paste_fit(page, composite_to_rgb(original), (margin + 18, panel_top + 54, margin + 317, panel_top + 304))

    d.rounded_rectangle([margin + 365, panel_top, margin + 700, panel_top + 320], radius=12, outline=(220, 220, 220), width=2)
    d.text((margin + 383, panel_top + 14), "成品预览", font=h1, fill=(0, 0, 0))
    paste_fit(page, preview, (margin + 383, panel_top + 54, margin + 682, panel_top + 304))

    d.rounded_rectangle([right_x, panel_top, W - margin, panel_top + 1120], radius=12, outline=(220, 220, 220), width=2)
    draw_color_list(d, counts, tag_to_color, right_x + 18, panel_top + 18, W - margin - right_x - 36, 1080, h1, small)

    ov_top = panel_top + 365
    d.rounded_rectangle([margin, ov_top, margin + 700, ov_top + 870], radius=12, outline=(220, 220, 220), width=2)
    d.text((margin + 18, ov_top + 14), "总览网格", font=h1, fill=(0, 0, 0))
    overview = draw_overview_grid(grid, tag_to_color, 660, 790, show_text=False)
    paste_fit(page, overview, (margin + 20, ov_top + 58, margin + 680, ov_top + 845))

    tips_y = H - 255
    d.rounded_rectangle([margin, tips_y, W - margin, H - 62], radius=14, fill=(248, 248, 244), outline=(215, 215, 205), width=2)
    tips = [
        "制作提示：先按分页图从左到右、从上到下摆放；每 5/10 格有辅助粗线，便于对齐拼板。",
        "默认白底按豆处理；只有明确要求“白底不放豆/空格版/透明背景/省豆/去掉白底”时才留空。",
        "本图纸按 MARD 221 标准色号最近 RGB 匹配生成；实际豆色、屏幕和打印颜色可能有轻微差异。",
        f"空格模式：{'开启' if blank_white else '关闭'}。输出包含 PDF、首页预览 PNG、成品预览 PNG、用量 CSV。",
    ]
    yy = tips_y + 22
    for line in tips:
        d.text((margin + 24, yy), line, font=small, fill=(50, 50, 50))
        yy += 38
    d.text((W - margin - 260, H - 42), "Generated by mard221_printable_pattern.py", font=tiny, fill=(120, 120, 120))
    return page


def make_section_page(grid, tag_to_color, sx: int, sy: int, sw: int, sh: int, page_no: int, total_pages: int) -> Image.Image:
    W, H = 1240, 1754
    page = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(page)
    title_font = find_font(32, bold=True)
    label_font = find_font(16)
    tag_font = find_font(12, bold=True)
    small = find_font(15)
    margin = 54
    d.text((margin, 38), f"MARD 分区色号图 {page_no}/{total_pages} — 行 {sy+1}-{sy+sh}，列 {sx+1}-{sx+sw}", font=title_font, fill=(0, 0, 0))
    grid_x, grid_y = margin + 54, 112
    max_grid_w, max_grid_h = 880, 1320
    cell = min(max_grid_w // sw, max_grid_h // sh)
    cell = max(18, min(32, cell))
    # adjust if too tall/wide
    while cell * sw > max_grid_w or cell * sh > max_grid_h:
        cell -= 1
    section_counts = Counter()
    # labels
    for xx in range(sw):
        col_num = sx + xx + 1
        if col_num == 1 or col_num % 5 == 0 or xx == 0 or xx == sw - 1:
            tw, th = text_size(d, str(col_num), label_font)
            d.text((grid_x + xx * cell + (cell - tw) / 2, grid_y - 24), str(col_num), font=label_font, fill=(0, 0, 0))
    for yy in range(sh):
        row_num = sy + yy + 1
        if row_num == 1 or row_num % 5 == 0 or yy == 0 or yy == sh - 1:
            tw, th = text_size(d, str(row_num), label_font)
            d.text((grid_x - tw - 8, grid_y + yy * cell + (cell - th) / 2), str(row_num), font=label_font, fill=(0, 0, 0))
    for yy in range(sh):
        for xx in range(sw):
            tag = grid[sy + yy][sx + xx]
            x0, y0 = grid_x + xx * cell, grid_y + yy * cell
            fill = (255, 255, 255) if tag is None else tag_to_color[tag]["rgb"]
            d.rectangle([x0, y0, x0 + cell, y0 + cell], fill=fill)
            if tag:
                section_counts[tag] += 1
                tf = tag_font if text_size(d, tag, tag_font)[0] <= cell - 2 else find_font(9, bold=True)
                tw, th = text_size(d, tag, tf)
                lum = sum(fill) / 3
                d.text((x0 + (cell - tw) / 2, y0 + (cell - th) / 2 - 1), tag, font=tf, fill=(0, 0, 0) if lum > 135 else (255, 255, 255))
    # grid lines after text for crisp border
    for xx in range(sw + 1):
        abs_col = sx + xx
        lw = 3 if abs_col % 10 == 0 else (2 if abs_col % 5 == 0 else 1)
        col = (35, 35, 35) if abs_col % 10 == 0 else ((95, 95, 95) if abs_col % 5 == 0 else (185, 185, 185))
        d.line([(grid_x + xx * cell, grid_y), (grid_x + xx * cell, grid_y + sh * cell)], fill=col, width=lw)
    for yy in range(sh + 1):
        abs_row = sy + yy
        lw = 3 if abs_row % 10 == 0 else (2 if abs_row % 5 == 0 else 1)
        col = (35, 35, 35) if abs_row % 10 == 0 else ((95, 95, 95) if abs_row % 5 == 0 else (185, 185, 185))
        d.line([(grid_x, grid_y + yy * cell), (grid_x + sw * cell, grid_y + yy * cell)], fill=col, width=lw)
    # section counts panel
    px = grid_x + sw * cell + 36
    d.rounded_rectangle([px, grid_y, W - margin, grid_y + min(1250, sh * cell)], radius=10, outline=(220, 220, 220), width=2)
    d.text((px + 16, grid_y + 16), "本区用色统计", font=find_font(22, bold=True), fill=(0, 0, 0))
    yy = grid_y + 58
    for tag, n in sorted(section_counts.items(), key=lambda kv: (-kv[1], kv[0])):
        if yy > H - 100:
            d.text((px + 16, yy), "…", font=small, fill=(120, 0, 0))
            break
        c = tag_to_color[tag]
        d.rectangle([px + 16, yy + 2, px + 42, yy + 22], fill=c["rgb"], outline=(70, 70, 70))
        d.text((px + 52, yy), f"{tag}  {n}", font=small, fill=(0, 0, 0))
        yy += 28
    d.text((margin, H - 50), "注：格内文字为 MARD 色号；每 5 格/10 格为辅助粗线。", font=small, fill=(90, 90, 90))
    return page


def write_counts_csv(path: Path, counts: Counter, tag_to_color: Dict[str, Dict]):
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["tag", "hex", "r", "g", "b", "count"])
        for tag, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
            c = tag_to_color[tag]
            w.writerow([tag, c["hex"], *c["rgb"], n])


def generate(input_path: Path, output_prefix: Path, palette_path: Path, args) -> Dict[str, str]:
    palette = load_palette(palette_path)
    original = Image.open(input_path)
    w, h, note, metrics = target_dimensions(original, args)
    grid, counts, tag_to_color, _sample = map_image(original, w, h, palette, blank_white=args.blank_white, blank_threshold=args.blank_threshold)
    preview_scale = max(4, min(18, 1200 // max(w, h)))
    preview = make_preview(grid, tag_to_color, scale=preview_scale)

    out_pdf = output_prefix.with_suffix(".pdf")
    out_page1 = output_prefix.with_name(output_prefix.name + "_page1.png")
    out_preview = output_prefix.with_name(output_prefix.name + "_preview.png")
    out_counts = output_prefix.with_name(output_prefix.name + "_counts.csv")
    out_preview.parent.mkdir(parents=True, exist_ok=True)

    preview.save(out_preview)
    write_counts_csv(out_counts, counts, tag_to_color)

    title = args.title or f"MARD 221 拼豆图纸 — {input_path.stem}"
    pages = [make_cover_page(title, original, preview, grid, counts, tag_to_color, note, metrics, args.blank_white)]
    seg = args.section_size
    total_sections = math.ceil(w / seg) * math.ceil(h / seg)
    pno = 1
    for sy in range(0, h, seg):
        for sx in range(0, w, seg):
            sw, sh = min(seg, w - sx), min(seg, h - sy)
            pno += 1
            pages.append(make_section_page(grid, tag_to_color, sx, sy, sw, sh, pno, total_sections + 1))
    pages[0].save(out_page1)
    pdf_pages = [p.convert("RGB") for p in pages]
    pdf_pages[0].save(out_pdf, save_all=True, append_images=pdf_pages[1:], resolution=150.0)
    return {
        "pdf": str(out_pdf),
        "page1": str(out_page1),
        "preview": str(out_preview),
        "counts": str(out_counts),
        "width": str(w),
        "height": str(h),
        "beads": str(sum(counts.values())),
        "colors": str(len(counts)),
        "note": note,
    }


def build_parser():
    p = argparse.ArgumentParser(description="Generate printable MARD 221 bead pattern PDF/PNG/CSV from an image.")
    p.add_argument("input", type=Path, help="input image")
    p.add_argument("--output-prefix", "-o", type=Path, required=True, help="output prefix, e.g. /tmp/mard_test")
    p.add_argument("--palette", type=Path, default=DEFAULT_PALETTE, help="MARD 221 palette JSON")
    p.add_argument("--size", type=parse_size, help="strict bead size WxH, e.g. 80x80 or 40x60")
    p.add_argument("--width", type=int, help="strict bead width, height keeps original ratio unless --height also set")
    p.add_argument("--height", type=int, help="strict bead height, width keeps original ratio unless --width also set")
    p.add_argument("--long-side", type=int, help="override auto long-side bead count, keeping original ratio")
    p.add_argument("--blank-white", action="store_true", help="treat near-white/transparent pixels as blank spaces; default is OFF")
    p.add_argument("--blank-threshold", type=int, default=245, help="RGB threshold for --blank-white")
    p.add_argument("--section-size", type=int, default=40, help="section page size, default 40x40")
    p.add_argument("--title", help="PDF title")
    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.section_size < 10 or args.section_size > 60:
        parser.error("--section-size must be 10..60")
    result = generate(args.input, args.output_prefix, args.palette, args)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

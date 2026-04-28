---
name: mard-pindou-pattern
description: Use when the user says “准备拼豆图纸生成”, “准备做拼豆图纸”, “我要生成拼豆底稿”, or sends a bead-pattern generation request for MARD 221 colors. Generates printable perler/bead PDF patterns, previews, section color-code pages, and usage CSV from an image.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [creative, mard, 拼豆, perler, beads, pdf, pillow]
    related_skills: []
---

# MARD 221 拼豆图纸生成

## Overview

This skill turns a user-supplied image into a printable MARD 221 拼豆图纸. It uses the local script:

```bash
~/.hermes/scripts/mard221_printable_pattern.py
```

The script uses Pillow to:

1. Read the input image.
2. Decide an appropriate bead-grid size when the user did not specify one.
3. Resize while preserving the original aspect ratio.
4. Match every bead to the nearest MARD 221 standard RGB color.
5. Export a finished preview PNG, a printable PDF, section color-code pages, and a usage CSV.

The MARD 221 palette is saved at:

- `~/.hermes/data/mard221_palette.json`
- `~/.hermes/data/mard221_palette.csv`

A portable copy is bundled in this skill folder:

- `references/mard221_palette.json`
- `scripts/mard221_printable_pattern.py`

## Trigger / First Reply

When the user says any of these or similar phrases:

- “准备拼豆图纸生成”
- “准备做拼豆图纸”
- “我要生成拼豆底稿”
- “帮我生成 MARD 拼豆图纸”
- “做拼豆 PDF 图纸”

First reply exactly:

> 准备好了，你在60秒内把图片发我就行。收到后我会按 MARD 221 色号，智能判断合适尺寸，参考打印版面生成：预览图、正式PDF图纸、分区色号图和用量表。

Then wait for the image. When the image arrives, generate the outputs automatically.

## Core Rules

### 1. Palette

Always use MARD 221 standard colors. The installed palette was scraped and cross-checked from:

- `https://www.pindou.online/colors`
- `https://peiseka.com/pindouseka.html`

The palette must contain exactly 221 unique color tags and fields at least:

- `tag`
- `hex`
- `rgb`

Primary runtime path:

```bash
~/.hermes/data/mard221_palette.json
```

### 2. Size Selection

Do **not** default to fixed `80×80`.

If the user explicitly says `80×80`, `40×60`, `29×29 拼板`, etc., use the specified size strictly.

If no size is specified, keep the original image ratio and choose an intelligent long side:

- simple image: 40–60
- normal character: 50–70
- anime avatar / bust: 70–90
- complex person / high-detail image: 90–120

The installed script implements a complexity heuristic based on edge density, color variety, and entropy.

### 3. White Background / Blank Spaces

Default: **white background is still beads**.

Only use blank/empty cells when the user explicitly says one of:

- “白底不放豆”
- “空格版”
- “透明背景”
- “省豆”
- “去掉白底”

In that case pass `--blank-white`.

### 4. Printable Layout

The PDF should follow a formal printable pattern layout:

- Page 1:
  - title
  - dimensions
  - total grid cells / bead count
  - color count
  - original image
  - finished preview
  - overview grid
  - right-side color list with color code / swatch / HEX / quantity
  - tips box
- Later pages:
  - about `40×40` section pages
  - row/column labels
  - MARD color code inside each cell
  - 5/10-grid helper thick lines
  - right-side local section usage statistics

### 5. Deliverables

Each generation must return the user these files:

- formal PDF pattern
- first-page preview PNG
- finished preview PNG
- usage CSV

In chat, attach files with `MEDIA:/absolute/path` when supported.

For this user, prefer converting the PDF into separate PNG page images and sending those page images directly, especially on WeChat where PDF/file delivery may fail or be missed. Keep the PDF/CSV locally available, but do not rely on PDF as the only deliverable.

PDF-to-PNG conversion recipe:

```bash
python - <<'PY'
from pathlib import Path
import fitz
pdf = Path('/tmp/mard_x.pdf')
outdir = Path('/tmp/mard_x_png_pages')
outdir.mkdir(exist_ok=True)
doc = fitz.open(str(pdf))
for i, page in enumerate(doc, start=1):
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
    pix.save(str(outdir / f'mard_x_page_{i:02d}.png'))
PY
```

If the user says the result feels low-resolution or blurry, use the original image path, crop away unnecessary empty margins if appropriate, lightly increase contrast/sharpness, and regenerate with a modestly higher bead grid such as 80×80 or an equivalent image-ratio-preserving size.

## Command Recipes

### Auto-size generation

```bash
python ~/.hermes/scripts/mard221_printable_pattern.py /path/to/input.png \
  --output-prefix /tmp/mard_pattern
```

Outputs:

- `/tmp/mard_pattern.pdf`
- `/tmp/mard_pattern_page1.png`
- `/tmp/mard_pattern_preview.png`
- `/tmp/mard_pattern_counts.csv`

### Strict size

```bash
python ~/.hermes/scripts/mard221_printable_pattern.py /path/to/input.png \
  --output-prefix /tmp/mard_pattern \
  --size 80x80
```

### Strict width or height while preserving ratio

```bash
python ~/.hermes/scripts/mard221_printable_pattern.py /path/to/input.png \
  --output-prefix /tmp/mard_pattern \
  --width 60
```

### Blank-white / space-saving version

Only when explicitly requested:

```bash
python ~/.hermes/scripts/mard221_printable_pattern.py /path/to/input.png \
  --output-prefix /tmp/mard_pattern \
  --blank-white
```

### Custom section size

Default is 40×40. Use only when needed:

```bash
python ~/.hermes/scripts/mard221_printable_pattern.py /path/to/input.png \
  --output-prefix /tmp/mard_pattern \
  --section-size 40
```

## Suggested Chat Workflow

1. Trigger phrase received → reply with the exact prepared message above. Do not change the user's trigger wording or the prepared reply wording.
2. Wait for the uploaded image. When the image arrives after this trigger, generate the pattern automatically immediately; do not wait for the user to say “生成” again. If the user first asks to describe an image and then says “就是这张图 / 按之前要求生成 / use this image”, treat the most recently uploaded/seen image as the input for this skill.
3. Inspect the user's trigger message and image message for explicit size or blank-white instructions.
4. Locate the image path. In WeChat/Hermes sessions, uploaded images are often cached under `~/.hermes/image_cache/` or profile-specific cache directories such as `~/.hermes/profiles/*/cache/images/`. If no direct path is provided, find the most recent plausible image and verify its dimensions/timestamp before using it:

```bash
python - <<'PY'
from pathlib import Path
from PIL import Image
import time
roots = [Path.home()/'.hermes/image_cache', Path.home()/'.hermes/profiles']
paths = []
for r in roots:
    if r.exists():
        paths += list(r.rglob('*.jpg')) + list(r.rglob('*.jpeg')) + list(r.rglob('*.png')) + list(r.rglob('*.webp'))
for p in sorted(paths, key=lambda p: p.stat().st_mtime, reverse=True)[:20]:
    try:
        im = Image.open(p)
        print(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(p.stat().st_mtime)), im.size, p)
    except Exception:
        pass
PY
```

5. Run the generator with a safe unique prefix, e.g.:

```bash
python ~/.hermes/scripts/mard221_printable_pattern.py "$IMAGE_PATH" \
  --output-prefix "/tmp/mard_$(date +%Y%m%d_%H%M%S)"
```

6. Verify outputs exist and are non-empty:

```bash
test -s /tmp/mard_x.pdf && test -s /tmp/mard_x_page1.png && \
test -s /tmp/mard_x_preview.png && test -s /tmp/mard_x_counts.csv
```

7. Convert the PDF into separate PNG page images and send those pages directly in chat. Keep the PDF/CSV available if needed, but final delivery should prioritize PNG pages split one by one:

```text
拼豆图纸已生成：这版为 [WxH]，共 [N] 颗豆，使用 [C] 种 MARD 色号。下面按 PNG 分页发你。

第1页：首页总览
MEDIA:/tmp/mard_x_png_pages/mard_x_page_01.png

第2页：分区图纸
MEDIA:/tmp/mard_x_png_pages/mard_x_page_02.png
...
```

## Verification Checklist

- [ ] Palette JSON/CSV exist under `~/.hermes/data/`.
- [ ] Palette contains exactly 221 unique MARD tags.
- [ ] Script exists and compiles: `python -m py_compile ~/.hermes/scripts/mard221_printable_pattern.py`.
- [ ] A test run produces PDF, page1 PNG, preview PNG, and counts CSV.
- [ ] Default behavior treats white as beads.
- [ ] `--blank-white` is used only when explicitly requested.

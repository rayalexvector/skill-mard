---
name: mard-pindou-pattern
description: Use when the user says “准备拼豆图纸生成” or sends an image to make a 拼豆/fuse-bead pattern. Prepare to receive the image, then generate a printable MARD 221 pattern with preview, labeled grids, and bead counts using the user's preferred layout rules.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [creative, pixel-art, fuse-beads, pindou, mard, printable]
    related_skills: [pixel-art]
---

# MARD 拼豆图纸生成

## Overview

This skill captures the user's preferred workflow for generating printable 拼豆/fuse-bead patterns from images.

The user's stable preferences:

- Palette: use the locally researched **MARD 221** palette, not arbitrary colors.
- Layout: follow the reference-style printable document: title page + original/preview + overview grid + color legend + sectioned labeled grids.
- Size: **choose dimensions intelligently** based on image complexity and craft usability unless the user explicitly specifies a size.
- If the user explicitly says “80×80 / 40×60 / 29×29拼板 / etc.”, obey that exact size.
- Do **not** automatically switch to a “white background as empty/no bead” version unless the user asks for it. By default, white background is treated as beads/cells.

Local assets already available on this machine:

- Palette CSV: `~/.hermes/data/mard221_palette.csv`
- Palette JSON: `~/.hermes/data/mard221_palette.json`
- Basic converter: `~/.hermes/scripts/mard221_template.py`
- Printable PDF generator: `~/.hermes/scripts/mard221_printable_pattern.py`

Bundled shareable files inside this skill directory:

- Palette JSON: `references/mard221_palette.json`
- Printable PDF generator: `scripts/mard221_printable_pattern.py`

When sharing this skill with another Hermes user, include the whole `mard-pindou-pattern/` folder so these bundled files travel with the skill.

## Primary Trigger

When the user says something like:

- “准备拼豆图纸生成”
- “准备做拼豆图纸”
- “等下我发图，你生成拼豆图纸”
- “我要生成拼豆底稿”

Reply briefly that you are ready and prepared to receive the image within about 60 seconds.

Recommended response:

> 准备好了，你在60秒内把图片发我就行。收到后我会按 MARD 221 色号，智能判断合适尺寸，参考你喜欢的打印版面生成：预览图、正式PDF图纸、分区色号图和用量表。

Do not ask many questions at this stage unless the user already mentions a constraint. The user wants a smooth “ready → send image → generate” workflow.

## Image Handling Workflow

When the image arrives:

1. Use the latest attached image path from the chat context.
2. Decide dimensions intelligently:
   - Simple icon / small object: about `40–60` cells on long side.
   - Anime avatar / character bust with facial details: about `70–90` cells on long side.
   - Complex full-body / scene / lots of small details: about `90–120` cells on long side, unless too impractical.
   - Keep aspect ratio unless the user specified exact width and height.
   - For square character images, common choices are `70×70`, `80×80`, or `90×90` depending on clarity.
3. Use MARD 221 nearest-color mapping.
4. Generate:
   - Printable PDF with overview + section pages.
   - Page 1 PNG preview of the document.
   - Pixel preview PNG.
   - CSV bead count sheet.
5. Verify outputs exist and inspect at least the homepage or a section page visually when practical.
6. Send the PDF plus page preview and counts CSV.

## Default Printable Layout

The preferred PDF structure:

### Page 1 — Overview

- Title: `MARD 221色拼豆图纸`
- Metadata:
  - size, e.g. `80×80 豆` or chosen dimensions
  - total bead/grid count
  - number of MARD colors used
  - palette note: `MARD 221（HEX/RGB近似匹配）`
- Two preview boxes:
  - `原图`
  - `成品预览`
- Large overview grid:
  - `WxH 总览网格（无色号，仅看效果）`
  - show grid lines and thicker guide lines
- Color legend on the right:
  - columns: 色号 / 色块 / HEX / 数量
  - sort by quantity descending
- Note box:
  - explain section pages, guide lines, and that cell text is MARD code.

### Section Pages

Split into printable sections, usually `40×40` cells per page.

Each section page should include:

- Title: `MARD拼豆分区图纸`
- Subtitle:
  - page number / section name
  - row range
  - column range
  - MARD 221 color code note
  - total pattern size
- Labeled grid:
  - row numbers on the left
  - column numbers on top
  - each colored cell labeled with MARD code
  - thicker lines every 10 cells, guide lines every 5 cells
- Optional right-side section color legend with counts.

## Dimension Rules

Do not force all patterns to `80×80`.

Use these defaults unless the user specifies otherwise:

| Image type | Suggested size |
|---|---:|
| very simple logo/icon | 40–50 long side |
| cute sticker/simple character | 50–70 long side |
| anime head/bust | 70–90 long side |
| detailed anime portrait | 80–100 long side |
| full-body character or complex art | 90–120 long side |

If uncertain, generate a practical size first and mention why. You may include a smaller/larger alternative only if useful, but do not surprise the user with unwanted variants.

## Background Rules

Default: treat white background as regular cells/beads.

Only use “white background empty/no bead” if the user explicitly asks for:

- 白底不放豆
- 空格版
- 透明背景
- 省豆
- 去掉白底

Do not automatically create an empty-background second version.

## Commands

Use the printable generator when available. On this machine the persistent script path is:

```bash
python ~/.hermes/scripts/mard221_printable_pattern.py /path/to/image.jpg \
  --width 80 --height 80 \
  --out /tmp/mard_pattern
```

For shared installs, prefer the bundled script and palette inside the skill directory. Replace `$SKILL_DIR` with the installed skill folder, usually `~/.hermes/skills/creative/mard-pindou-pattern`:

```bash
python "$SKILL_DIR/scripts/mard221_printable_pattern.py" /path/to/image.jpg \
  --palette "$SKILL_DIR/references/mard221_palette.json" \
  --width 80 --height 80 \
  --out /tmp/mard_pattern
```

If only a long side is chosen and the script supports auto-height:

```bash
python "$SKILL_DIR/scripts/mard221_printable_pattern.py" /path/to/image.jpg \
  --palette "$SKILL_DIR/references/mard221_palette.json" \
  --width 80 \
  --out /tmp/mard_pattern
```

For exact user sizes, pass both `--width` and `--height`.

For explicitly requested empty-background version:

```bash
python "$SKILL_DIR/scripts/mard221_printable_pattern.py" /path/to/image.jpg \
  --palette "$SKILL_DIR/references/mard221_palette.json" \
  --width 80 --height 80 \
  --empty-white-threshold 248 \
  --out /tmp/mard_pattern_empty
```

## Delivery Format

Send concise Chinese summary with native media attachments:

```text
做好了：这版我按 [WxH] 生成，使用 MARD 221，共 [N] 色，[M] 格/颗。

PDF：
MEDIA:/tmp/xxx.pdf

首页预览：
MEDIA:/tmp/xxx_page1.png

成品预览：
MEDIA:/tmp/xxx_preview.png

用量表：
MEDIA:/tmp/xxx_counts.csv
```

If the size was chosen automatically, include one short sentence explaining the choice, e.g.:

> 这张图细节集中在脸和发丝，我选了80×80，兼顾清晰度和工作量。

## Common Pitfalls

1. **Forcing 80×80 because the reference screenshot used it.** The user explicitly corrected this. Choose intelligently unless exact size is requested.
2. **Auto-generating white-background-empty versions.** Do not do this unless requested.
3. **Changing palettes.** Keep MARD 221 unless the user explicitly asks for another brand/palette.
4. **Sending only a raw grid image.** The user prefers the printable PDF-style layout with overview, legend, and section pages.
5. **Skipping verification.** At minimum check that PDF/PNG/CSV files exist; visually inspect the overview/section page when feasible.
6. **Too many questions before receiving the image.** For the trigger phrase, just say ready and wait for the image.

## Verification Checklist

- [ ] MARD 221 palette used.
- [ ] Dimensions chosen intelligently or exact user size obeyed.
- [ ] White background behavior matches user request.
- [ ] PDF created.
- [ ] Page 1 PNG created.
- [ ] Preview PNG created.
- [ ] Counts CSV created.
- [ ] Section grids have row/column numbers and MARD codes.
- [ ] Final response includes media links and a compact summary.

# skill-mard

这是一个用于 Hermes 的拼豆图纸生成 skill：把用户发送的图片转换成可打印的 **MARD 221 色号拼豆 / fuse-bead 图纸**。

它会生成：

- 可打印 PDF 图纸（本地保留）
- PDF 每页转换后的 PNG 分页图片（聊天里优先分开发送）
- 首页总览 PNG
- 成品像素 / 拼豆预览 PNG
- 拼豆用量统计 CSV

## Hermes 安装方式

### 推荐：HTTPS 安装

公开仓库使用 HTTPS 安装即可，不需要 GitHub 账号，也不需要配置 SSH：

```bash
mkdir -p ~/.hermes/skills/creative
git clone https://github.com/rayalexvector/skill-mard.git ~/.hermes/skills/creative/mard-pindou-pattern
```

### 可选：SSH 安装

如果你的环境已经配置了 GitHub SSH，也可以使用：

```bash
mkdir -p ~/.hermes/skills/creative
git clone git@github.com:rayalexvector/skill-mard.git ~/.hermes/skills/creative/mard-pindou-pattern
```

安装后，重启 Hermes，或在已有会话里使用 `/reset` 让 skill 生效。

如果缺少依赖，可以安装：

```bash
pip install pillow pymupdf
# Linux 环境如果 PDF 中文标签字体缺失，可安装：
sudo apt install fonts-noto-cjk
```

## 使用方式

在 Hermes 里发送触发语，例如：

```text
准备拼豆图纸生成
```

Hermes 会按固定回复确认已准备好接收图片：

```text
准备好了，你在60秒内把图片发我就行。收到后我会按 MARD 221 色号，智能判断合适尺寸，参考打印版面生成：预览图、正式PDF图纸、分区色号图和用量表。
```

随后直接发送图片即可。图片到达后，Hermes 会**自动开始生成拼豆图纸**，不需要再补一句“生成”。

## skill 内置规则

- 使用 MARD 221 标准色号。
- 除非用户明确指定尺寸，否则由 Hermes 根据图片内容智能判断图纸尺寸。
- 不会因为示例是 80×80 就默认固定生成 80×80。
- 默认把白色背景也当作拼豆处理。
- 只有用户明确要求“白底不放豆 / 空格版 / 透明背景 / 省豆 / 去掉白底”时，才生成空白背景版本。
- 若结果显得分辨率低或模糊，可裁掉多余边缘、轻微增强对比/锐度，并适度提升豆数。
- 聊天交付时优先把 PDF 转成 PNG 分页图片，一页一张分开发送。

## 手动脚本用法

如果不通过 Hermes skill，也可以直接运行脚本：

```bash
python scripts/mard221_printable_pattern.py input.jpg \
  --palette references/mard221_palette.json \
  --output-prefix /tmp/mard_pattern
```

指定精确尺寸：

```bash
python scripts/mard221_printable_pattern.py input.jpg \
  --palette references/mard221_palette.json \
  --size 80x80 \
  --output-prefix /tmp/mard_pattern
```

只指定长边并保持原图比例：

```bash
python scripts/mard221_printable_pattern.py input.jpg \
  --palette references/mard221_palette.json \
  --long-side 80 \
  --output-prefix /tmp/mard_pattern
```

如果明确需要“白底不放豆 / 空格版”：

```bash
python scripts/mard221_printable_pattern.py input.jpg \
  --palette references/mard221_palette.json \
  --size 80x80 \
  --blank-white \
  --output-prefix /tmp/mard_pattern_empty
```

输出文件：

```text
/tmp/mard_pattern.pdf
/tmp/mard_pattern_page1.png
/tmp/mard_pattern_preview.png
/tmp/mard_pattern_counts.csv
```

## PDF 转 PNG 分页

聊天平台不一定稳定接收 PDF；推荐把 PDF 每页转成 PNG 后分开发送：

```bash
python - <<'PY'
from pathlib import Path
import fitz
pdf = Path('/tmp/mard_pattern.pdf')
outdir = Path('/tmp/mard_pattern_png_pages')
outdir.mkdir(exist_ok=True)
doc = fitz.open(str(pdf))
for i, page in enumerate(doc, start=1):
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
    pix.save(str(outdir / f'mard_pattern_page_{i:02d}.png'))
PY
```

## 文件结构

```text
SKILL.md
README.md
LICENSE
scripts/mard221_printable_pattern.py
references/mard221_palette.json
```

## 许可证

MIT

# mard

这是一个用于 Hermes 的拼豆图纸生成 skill：可以把用户发送的图片转换成可打印的 **MARD 221 色号拼豆 / fuse-bead 图纸**。

它会生成：

- 可打印的 PDF 图纸
- 首页总览 PNG
- 成品像素 / 拼豆预览 PNG
- 按分区拆分的 MARD 色号网格图
- 拼豆用量统计 CSV

## Hermes 安装方式

### 推荐：HTTPS 安装

公开仓库使用 HTTPS 安装即可，不需要 GitHub 账号，也不需要配置 SSH：

```bash
mkdir -p ~/.hermes/skills/creative
git clone https://github.com/rayalexvector/mard.git ~/.hermes/skills/creative/mard-pindou-pattern
```

### 可选：SSH 安装

如果你的环境已经配置了 GitHub SSH，也可以使用：

```bash
mkdir -p ~/.hermes/skills/creative
git clone git@github.com:rayalexvector/mard.git ~/.hermes/skills/creative/mard-pindou-pattern
```

安装后，重启 Hermes，或在已有会话里使用 `/reset` 让 skill 生效。

如果缺少依赖，可以安装：

```bash
pip install pillow
# Linux 环境如果 PDF 中文标签字体缺失，可安装：
sudo apt install fonts-noto-cjk
```

## 使用方式

在 Hermes 里发送：

```text
准备拼豆图纸生成
```

Hermes 会回复已准备好接收图片。随后发送图片，它会按照 MARD 221 色号生成可打印的拼豆图纸。

## skill 内置规则

- 使用 MARD 221 标准色号。
- 除非用户明确指定尺寸，否则由 Hermes 根据图片内容智能判断图纸尺寸。
- 不会因为示例是 80×80 就默认固定生成 80×80。
- 默认把白色背景也当作拼豆处理。
- 只有用户明确要求“白底不放豆 / 空格版”时，才生成空白背景版本。
- 输出 PDF、预览图、分区色号图和用量统计 CSV。

## 手动脚本用法

如果不通过 Hermes skill，也可以直接运行脚本：

```bash
python scripts/mard221_printable_pattern.py input.jpg \
  --palette references/mard221_palette.json \
  --width 80 \
  --out /tmp/mard_pattern
```

指定精确尺寸：

```bash
python scripts/mard221_printable_pattern.py input.jpg \
  --palette references/mard221_palette.json \
  --width 80 --height 80 \
  --out /tmp/mard_pattern
```

如果明确需要“白底不放豆 / 空格版”：

```bash
python scripts/mard221_printable_pattern.py input.jpg \
  --palette references/mard221_palette.json \
  --width 80 --height 80 \
  --empty-white-threshold 248 \
  --out /tmp/mard_pattern_empty
```

## 文件结构

```text
SKILL.md
scripts/mard221_printable_pattern.py
references/mard221_palette.json
```

## 许可证

MIT

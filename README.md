# mard

Hermes skill for generating printable **MARD 221 拼豆 / fuse-bead patterns** from images.

It creates:

- printable PDF pattern
- page 1 overview PNG
- pixel/bead preview PNG
- MARD color-code section grids
- bead count CSV

## Hermes SSH install

```bash
mkdir -p ~/.hermes/skills/creative
git clone git@github.com:rayalexvector/mard.git ~/.hermes/skills/creative/mard-pindou-pattern
```

Then restart Hermes or start a new session. In an existing chat, use `/reset` if available.

Optional dependencies if missing:

```bash
pip install pillow
# Linux only, for Chinese PDF labels if fonts are missing:
sudo apt install fonts-noto-cjk
```

## Usage

Say:

```text
准备拼豆图纸生成
```

Hermes should reply that it is ready to receive your image. Send an image, and it will generate a printable MARD 221 pattern.

## Rules encoded in the skill

- Uses MARD 221 color codes.
- Chooses dimensions intelligently unless the user explicitly specifies a size.
- Does not default to 80×80 just because examples use 80×80.
- Treats white background as beads by default.
- Only uses empty/no-bead white background when explicitly requested.
- Outputs PDF + previews + CSV counts.

## Manual script usage

```bash
python scripts/mard221_printable_pattern.py input.jpg   --palette references/mard221_palette.json   --width 80   --out /tmp/mard_pattern
```

For exact dimensions:

```bash
python scripts/mard221_printable_pattern.py input.jpg   --palette references/mard221_palette.json   --width 80 --height 80   --out /tmp/mard_pattern
```

For an explicitly requested white-background-empty version:

```bash
python scripts/mard221_printable_pattern.py input.jpg   --palette references/mard221_palette.json   --width 80 --height 80   --empty-white-threshold 248   --out /tmp/mard_pattern_empty
```

## Files

```text
SKILL.md
scripts/mard221_printable_pattern.py
references/mard221_palette.json
```

## License

MIT

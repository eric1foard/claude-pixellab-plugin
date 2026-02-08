---
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
---

# /pixellab - Generate Pixel Art

You are a pixel art generation assistant. The user wants you to generate pixel art using the PixelLab API.

## Instructions

1. **Parse the user's request** to determine:
   - What to generate (description)
   - Desired size (default 64x64 if not specified)
   - Any style preferences (retro, modern, detailed, etc.)
   - Whether it's a new sprite, animation, rotation, or edit

2. **Read the skill documentation** for parameter details:
   ```
   Read skills/pixellab-api/SKILL.md
   ```

3. **Choose the right endpoint:**
   - New sprite from text → `generate-pixflux`
   - Match existing style → `generate-bitforge` with `--style-image`
   - Animation → `animate-text` (quick, 64x64) or `animate-skeleton` (precise)
   - Rotation → `rotate`
   - Edit existing → `inpaint`

4. **Run the helper script** with appropriate parameters:
   ```bash
   python3 skills/pixellab-api/scripts/pixellab.py <subcommand> [options]
   ```

5. **Report results** - show the output JSON, confirm files were created, and report cost.

## Quick Reference

### Sizes
- `16x16` / `32x32` - retro sprites, items
- `64x64` - standard (required for animate-text)
- `128x128` - detailed characters
- `256x256` / `400x400` - large artwork (pixflux only for 400)

### Style Shortcuts
- "retro" → `--outline "single color black outline" --shading "flat shading" --detail "low detail"`
- "classic" → `--outline "single color black outline" --shading "basic shading" --detail "medium detail"`
- "modern" → `--outline "selective outline" --shading "medium shading" --detail "medium detail"`
- "detailed" → `--outline "selective outline" --shading "detailed shading" --detail "highly detailed"`
- "lineless" → `--outline "lineless" --shading "detailed shading" --detail "highly detailed"`

### Examples

**Simple generation (most common):**
```bash
python3 skills/pixellab-api/scripts/pixellab.py generate-pixflux \
  --description "USER'S DESCRIPTION HERE" \
  --width 64 --height 64 \
  --outline "single color black outline" \
  --shading "medium shading" \
  --no-background \
  --output ./output.png
```

**Animation:**
```bash
python3 skills/pixellab-api/scripts/pixellab.py animate-text \
  --description "CHARACTER DESCRIPTION" \
  --action "walk" \
  --reference-image ./character.png \
  --direction east \
  --spritesheet \
  --output ./walk
```

**Check balance:**
```bash
python3 skills/pixellab-api/scripts/pixellab.py balance
```

## Output Format

The script outputs JSON to stdout:
```json
{"success": true, "output_files": ["./sprite.png"], "cost_usd": 0.005}
```

Always tell the user which files were created and the cost.

## Arguments

The user's input after `/pixellab` is their request. Parse it naturally:
- `/pixellab a blue slime monster 32x32` → generate-pixflux, 32x32, "a blue slime monster"
- `/pixellab animate walk cycle for knight.png` → animate-text with reference
- `/pixellab rotate knight.png to face north` → rotate endpoint
- `/pixellab edit knight.png add a hat` → inpaint (need mask)
- `/pixellab balance` → check balance

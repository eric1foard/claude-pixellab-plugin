---
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
---

# /pixellab - Generate Pixel Art

You are a pixel art generation assistant using the PixelLab v2 API (Pro endpoints).

## Instructions

1. **Parse the user's request** to determine:
   - What to generate (description)
   - Desired size (default 64x64 if not specified)
   - Whether it's a new sprite, animation, rotation, edit, or other operation

2. **Read the skill documentation** for parameter details:
   ```
   Read skills/pixellab-api/SKILL.md
   ```

3. **Choose the right subcommand:**
   - New sprite from text → `generate`
   - Match existing style → `generate-with-style` with `--style-images`
   - Animation → `animate` with reference image and action
   - 8 rotations → `rotate-8`
   - Edit existing art → `inpaint` with mask
   - In-between frames → `interpolate`
   - Edit animation → `edit-animation`
   - Transfer outfit → `transfer-outfit`

4. **Run the helper script:**
   ```bash
   python3 skills/pixellab-api/scripts/pixellab.py <subcommand> [options]
   ```

5. **Report results** - show output JSON, confirm files created, report cost.

## Quick Reference

### Sizes (generate endpoint)
- `32x32` - 64 variations returned
- `64x64` - 16 variations returned (default)
- `128x128` - 4 variations returned
- `256x256` - 1 variation returned

By default only the first variation is saved. Use `--all` for all variations.

### Examples

**Simple generation (most common):**
```bash
python3 skills/pixellab-api/scripts/pixellab.py generate \
  --description "USER'S DESCRIPTION HERE" \
  --width 64 --height 64 \
  --no-background \
  --output ./output.png
```

**Animation:**
```bash
python3 skills/pixellab-api/scripts/pixellab.py animate \
  --reference-image ./character.png \
  --ref-width 64 --ref-height 64 \
  --action "walk" \
  --width 64 --height 64 \
  --spritesheet \
  --output ./walk
```

**8 rotations from existing sprite:**
```bash
python3 skills/pixellab-api/scripts/pixellab.py rotate-8 \
  --method rotate_character \
  --reference-image ./character.png \
  --width 64 --height 64 \
  --output ./character_rot
```

**Check balance:**
```bash
python3 skills/pixellab-api/scripts/pixellab.py balance
```

## Output Format

The script outputs JSON to stdout:
```json
{"success": true, "output_files": ["./sprite.png"], "cost_usd": 0.18, "total_variations": 16}
```

Always tell the user which files were created and the cost.

## Arguments

Parse the user's input after `/pixellab` naturally:
- `/pixellab a blue slime monster 32x32` → generate, 32x32, "a blue slime monster"
- `/pixellab animate walk cycle for knight.png` → animate with reference
- `/pixellab rotate knight.png all 8 directions` → rotate-8
- `/pixellab edit knight.png add a hat` → inpaint (need mask)
- `/pixellab balance` → check balance

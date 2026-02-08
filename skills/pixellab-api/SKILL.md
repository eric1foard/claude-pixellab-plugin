# PixelLab API - Pixel Art Generation

Generate pixel art sprites, animations, and tilesets using the PixelLab API. This skill wraps all PixelLab endpoints via a helper script that handles authentication, image encoding, and file I/O.

## Prerequisites

The environment variable `PIXELLAB_API_KEY` must be set. Check balance before expensive operations:

```bash
python3 skills/pixellab-api/scripts/pixellab.py balance
```

## Endpoint Selection Guide

| Task | Endpoint | Subcommand | Best For |
|------|----------|------------|----------|
| Create sprite from text | Pixflux | `generate-pixflux` | General pixel art, larger sizes (up to 400x400) |
| Create sprite with style ref | Bitforge | `generate-bitforge` | Matching existing art style, up to 200x200 |
| Animate with poses | Skeleton | `animate-skeleton` | Walk cycles, attacks with precise control |
| Animate with text | Text | `animate-text` | Quick animations, 64x64 only |
| Rotate character | Rotate | `rotate` | Character turnarounds, direction sheets |
| Edit existing art | Inpaint | `inpaint` | Modifying specific regions of existing sprites |
| Get character pose | Skeleton Est. | `estimate-skeleton` | Extract keypoints before animating |

**Decision flow:**
1. Creating new art from scratch? Use **generate-pixflux** (most flexible).
2. Need to match an existing style? Use **generate-bitforge** with `--style-image`.
3. Animating an existing character? Use **estimate-skeleton** first, then **animate-skeleton**.
4. Quick animation without skeleton setup? Use **animate-text** (64x64 only).
5. Need a character from a different angle? Use **rotate**.
6. Editing part of existing art? Use **inpaint** with a mask.

## Helper Script Interface

**Location:** `skills/pixellab-api/scripts/pixellab.py`
**Runtime:** Python 3 (stdlib only, no pip)

All subcommands output JSON to stdout:

```json
{"success": true, "output_files": ["./knight.png"], "cost_usd": 0.005}
```

On error:
```json
{"success": false, "error": "HTTP 402: Insufficient credits"}
```

### Common Options

| Option | Description |
|--------|-------------|
| `--output`, `-o` | Output file path (or base name for animations) |
| `--width`, `--height` | Image dimensions in pixels |
| `--outline` | `single color black outline`, `single color outline`, `selective outline`, `lineless` |
| `--shading` | `flat shading`, `basic shading`, `medium shading`, `detailed shading`, `highly detailed shading` |
| `--detail` | `low detail`, `medium detail`, `highly detailed` |
| `--view` | `side`, `low top-down`, `high top-down` |
| `--direction` | `north`, `north-east`, `east`, `south-east`, `south`, `south-west`, `west`, `north-west` |
| `--no-background` | Transparent background |
| `--seed` | Integer seed for reproducibility |
| `--spritesheet` | (animations only) Also output a horizontal spritesheet |

### Quick Examples

**Generate a character sprite:**
```bash
python3 skills/pixellab-api/scripts/pixellab.py generate-pixflux \
  --description "a knight in silver armor holding a sword" \
  --width 64 --height 64 \
  --outline "single color black outline" \
  --shading "medium shading" \
  --no-background \
  --output ./knight.png
```

**Generate with style transfer:**
```bash
python3 skills/pixellab-api/scripts/pixellab.py generate-bitforge \
  --description "a red dragon" \
  --width 64 --height 64 \
  --style-image ./reference_style.png \
  --style-strength 50 \
  --no-background \
  --output ./dragon.png
```

**Animate a walk cycle:**
```bash
# Step 1: Estimate skeleton from reference
python3 skills/pixellab-api/scripts/pixellab.py estimate-skeleton \
  --image ./knight.png \
  --output ./knight_skeleton.json

# Step 2: Create animation keypoints (array of 4 frames, each an array of points)
# Write the keypoints JSON file with modified poses per frame

# Step 3: Generate animation
python3 skills/pixellab-api/scripts/pixellab.py animate-skeleton \
  --reference-image ./knight.png \
  --skeleton-keypoints ./walk_keypoints.json \
  --width 64 --height 64 \
  --direction east \
  --spritesheet \
  --output ./knight_walk
```

**Text-guided animation:**
```bash
python3 skills/pixellab-api/scripts/pixellab.py animate-text \
  --description "a knight in silver armor" \
  --action "walk" \
  --reference-image ./knight.png \
  --n-frames 8 \
  --direction east \
  --spritesheet \
  --output ./knight_walk
```

**Rotate a character:**
```bash
python3 skills/pixellab-api/scripts/pixellab.py rotate \
  --from-image ./knight_south.png \
  --from-direction south \
  --to-direction east \
  --width 64 --height 64 \
  --output ./knight_east.png
```

**Inpaint/edit existing art:**
```bash
python3 skills/pixellab-api/scripts/pixellab.py inpaint \
  --description "a golden crown" \
  --inpainting-image ./knight.png \
  --mask-image ./head_mask.png \
  --width 64 --height 64 \
  --output ./knight_crowned.png
```

## Common Pixel Art Sizes

| Use Case | Size | Notes |
|----------|------|-------|
| Small game sprites | 16x16, 32x32 | Retro RPG characters, items |
| Standard sprites | 64x64 | Most versatile, required for animate-text |
| Detailed characters | 128x128 | Good balance of detail and pixel feel |
| Large artwork | 256x256, 400x400 | Splash art, detailed scenes (pixflux only for 400) |
| Tilesets | 16x16, 32x32 | Individual tiles |
| Icons/items | 16x16, 32x32 | Inventory items, UI elements |

## Style Presets

**Retro (NES/Game Boy era):**
- `--outline "single color black outline" --shading "flat shading" --detail "low detail"`
- Best at 16x16 or 32x32

**Classic (SNES/GBA era):**
- `--outline "single color black outline" --shading "basic shading" --detail "medium detail"`
- Best at 32x32 or 64x64

**Modern pixel art:**
- `--outline "selective outline" --shading "medium shading" --detail "medium detail"`
- Best at 64x64 or 128x128

**Detailed/HD pixel art:**
- `--outline "selective outline" --shading "detailed shading" --detail "highly detailed"`
- Best at 128x128 to 400x400

**Lineless/soft:**
- `--outline "lineless" --shading "detailed shading" --detail "highly detailed"`
- Best at 64x64+

## Workflow

1. **Determine the task** - what kind of pixel art is needed?
2. **Choose the endpoint** using the selection guide above
3. **Select appropriate size** based on the use case
4. **Pick style parameters** or use a preset
5. **Run the script** with chosen parameters
6. **Check the output** - read the JSON result and verify the file was created
7. **Iterate if needed** - adjust description, style, or seed and regenerate

## Animation Workflow (Skeleton-Based)

For best results with character animation:

1. **Generate a reference character** with `generate-pixflux` (transparent background)
2. **Estimate the skeleton** with `estimate-skeleton` to get keypoints
3. **Design animation poses** by modifying keypoint positions for each frame (4 frames)
4. **Save keypoints** as a JSON file: `[[frame0_points], [frame1_points], [frame2_points], [frame3_points]]`
5. **Generate animation** with `animate-skeleton`
6. Use `--spritesheet` flag to get a combined horizontal strip

### Skeleton Keypoint Format

Each point: `{"x": float, "y": float, "label": "LABEL", "z_index": int}`

Labels: `NOSE`, `NECK`, `RIGHT SHOULDER`, `RIGHT ELBOW`, `RIGHT ARM`, `LEFT SHOULDER`, `LEFT ELBOW`, `LEFT ARM`, `RIGHT HIP`, `RIGHT KNEE`, `RIGHT LEG`, `LEFT HIP`, `LEFT KNEE`, `LEFT LEG`, `RIGHT EYE`, `LEFT EYE`, `RIGHT EAR`, `LEFT EAR`

## Full API Reference

For complete parameter documentation including all ranges, defaults, and response schemas, see `references/api-endpoints.md`.

# PixelLab API v2 - Pixel Art Generation

Generate pixel art sprites, animations, and tilesets using the PixelLab v2 API (Pro endpoints). This skill wraps all endpoints via a helper script that handles authentication, image encoding, and file I/O.

## Prerequisites

The environment variable `PIXELLAB_API_KEY` must be set. Check balance before expensive operations:

```bash
python3 skills/pixellab-api/scripts/pixellab.py balance
```

## Endpoint Selection Guide

| Task | Subcommand | Best For |
|------|------------|----------|
| Create sprite from text | `generate` | General pixel art, up to 256x256, returns variations |
| Create with style reference | `generate-with-style` | Matching existing art style, 16-256px |
| Animate character | `animate` | Text-guided animation, 32-256px |
| 8-direction rotation sheet | `rotate-8` | Character turnarounds, 32-84px |
| Edit region of art | `inpaint` | Modify specific area with mask, 32-256px |
| Batch edit images | `edit` | Edit multiple images with text or reference |
| Frame interpolation | `interpolate` | Generate in-between frames, 16-128px |
| Edit animation | `edit-animation` | Modify existing animation, 16-128px |
| Transfer outfit | `transfer-outfit` | Apply outfit to animation frames, 16-128px |
| Get character pose | `estimate-skeleton` | Extract keypoints for animation |

**Decision flow:**
1. Creating new art from scratch? Use **generate** (simplest, most flexible).
2. Need to match an existing style? Use **generate-with-style** with style images.
3. Animating a character? Use **animate** with a reference image.
4. Need all 8 directions? Use **rotate-8**.
5. Editing part of existing art? Use **inpaint** with a mask.
6. Generating in-between frames? Use **interpolate**.

## Helper Script Interface

**Location:** `skills/pixellab-api/scripts/pixellab.py`
**Runtime:** Python 3 (stdlib only, no pip)
**API:** PixelLab v2 (Pro endpoints)

All subcommands output JSON to stdout:

```json
{"success": true, "output_files": ["./sprite.png"], "cost_usd": 0.18, "total_variations": 16}
```

On error:
```json
{"success": false, "error": "HTTP 402: Insufficient credits"}
```

## Variation Counts by Size

The v2 generate endpoints return multiple variations per call:

| Size | Variations |
|------|-----------|
| 32x32 | 64 |
| 64x64 | 16 |
| 128x128 | 4 |
| 256x256 | 1 |

By default, only the first variation is saved. Use `--all` to save all, or `--pick N` to choose a specific one.

## Quick Examples

**Generate a character sprite (saves first variation):**
```bash
python3 skills/pixellab-api/scripts/pixellab.py generate \
  --description "a knight in silver armor holding a sword" \
  --width 64 --height 64 \
  --no-background \
  --output ./knight.png
```

**Generate with style transfer:**
```bash
python3 skills/pixellab-api/scripts/pixellab.py generate-with-style \
  --description "a red dragon" \
  --style-images ./reference_style.png \
  --width 64 --height 64 \
  --no-background \
  --output ./dragon.png
```

**Animate a walk cycle:**
```bash
python3 skills/pixellab-api/scripts/pixellab.py animate \
  --reference-image ./knight.png \
  --ref-width 64 --ref-height 64 \
  --action "walk" \
  --width 64 --height 64 \
  --spritesheet \
  --output ./knight_walk
```

**Generate 8-direction rotation sheet:**
```bash
python3 skills/pixellab-api/scripts/pixellab.py rotate-8 \
  --method rotate_character \
  --reference-image ./knight.png \
  --width 64 --height 64 \
  --output ./knight_rot
```

**Inpaint/edit existing art:**
```bash
python3 skills/pixellab-api/scripts/pixellab.py inpaint \
  --description "a golden crown" \
  --inpainting-image ./knight.png \
  --mask-image ./head_mask.png \
  --output ./knight_crowned.png
```

**Interpolate between keyframes:**
```bash
python3 skills/pixellab-api/scripts/pixellab.py interpolate \
  --start-image ./frame_start.png \
  --end-image ./frame_end.png \
  --action "swinging sword" \
  --width 64 --height 64 \
  --spritesheet \
  --output ./attack
```

## Common Pixel Art Sizes

| Use Case | Size | Notes |
|----------|------|-------|
| Small game sprites | 32x32 | Retro characters, items (64 variations) |
| Standard sprites | 64x64 | Most versatile (16 variations) |
| Detailed characters | 128x128 | Good detail (4 variations) |
| Large artwork | 256x256 | Maximum detail (1 variation) |

## Workflow

1. **Determine the task** - what kind of pixel art is needed?
2. **Choose the endpoint** using the selection guide above
3. **Select appropriate size** based on use case
4. **Run the script** with chosen parameters
5. **Check the output** - read the JSON result and verify files were created
6. **Iterate if needed** - adjust description or seed and regenerate

## Full API Reference

For complete parameter documentation, see `references/api-endpoints.md`.

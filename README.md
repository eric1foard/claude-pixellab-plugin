# Claude PixelLab Plugin

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) plugin that generates pixel art sprites, animations, and tilesets using the [PixelLab](https://www.pixellab.ai/) v2 API.

## Features

- **Sprite generation** - Create pixel art from text descriptions (32x32 to 256x256)
- **Style-guided generation** - Generate art matching a reference style
- **Animation** - Produce walk cycles, attacks, and other animations from a reference image
- **8-direction rotation** - Generate all 8 directional views of a character
- **Inpainting** - Edit specific regions of existing pixel art with a mask
- **Batch editing** - Edit multiple images with text or a reference
- **Frame interpolation** - Generate in-between animation frames
- **Animation editing** - Modify existing animation frames
- **Outfit transfer** - Apply an outfit across animation frames
- **Skeleton estimation** - Extract character keypoints for animation

## Installation

1. Get a PixelLab API key from [pixellab.ai](https://www.pixellab.ai/)
2. Set the environment variable:
   ```bash
   export PIXELLAB_API_KEY="your-api-key"
   ```
3. Install the plugin in Claude Code:
   ```
   /install-plugin https://github.com/eric1foard/claude-pixellab-plugin
   ```

## Usage

Use the `/pixellab` slash command in Claude Code:

```
/pixellab a knight in silver armor 64x64
/pixellab animate walk cycle for knight.png
/pixellab rotate knight.png all 8 directions
/pixellab balance
```

Or ask Claude directly -- the plugin skill will be used automatically when you ask for pixel art generation.

### Examples

**Generate a sprite:**
```bash
python3 skills/pixellab-api/scripts/pixellab.py generate \
  --description "a knight in silver armor holding a sword" \
  --width 64 --height 64 \
  --no-background \
  --output ./knight.png
```

**Animate a character:**
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

**Check balance:**
```bash
python3 skills/pixellab-api/scripts/pixellab.py balance
```

### Output Sizes and Variations

The generate endpoints return multiple variations per call:

| Size | Variations |
|------|-----------|
| 32x32 | 64 |
| 64x64 | 16 |
| 128x128 | 4 |
| 256x256 | 1 |

By default only the first variation is saved. Use `--all` to save all variations, or `--pick N` to choose a specific one.

## Requirements

- Python 3 (stdlib only, no pip dependencies)
- A PixelLab API key with credits or an active subscription

## Project Structure

```
.claude-plugin/plugin.json    # Plugin metadata
commands/pixellab.md          # /pixellab slash command definition
skills/pixellab-api/
  SKILL.md                    # Skill documentation for Claude
  references/api-endpoints.md # Full PixelLab v2 API reference
  scripts/pixellab.py         # CLI helper script (all endpoints)
```

## License

MIT

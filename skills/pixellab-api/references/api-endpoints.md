# PixelLab API v2 - Complete Endpoint Reference

Base URL: `https://api.pixellab.ai/v2`

Authentication: `Authorization: Bearer YOUR_API_TOKEN`

## Error Codes

| HTTP | Meaning |
|------|---------|
| 200 | Success |
| 401 | Invalid API token |
| 402 | Insufficient credits |
| 403 | Not authenticated |
| 422 | Validation error (check parameter ranges) |
| 429 | Too many requests |

---

## POST /generate-image-v2

Generate pixel art from text description. Returns multiple variations.

**Sizes:** 32x32 (64 images), 64x64 (16), 128x128 (4), 256x256 (1)

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `description` | string | Yes | - | Text description |
| `image_size` | {width, height} | Yes | - | 32/64/128/256 square |
| `reference_images` | Base64Image[] | No | - | Up to 4 guidance images |
| `style_image` | Base64Image | No | - | Style reference |
| `no_background` | bool | No | true | Transparent background |
| `seed` | int | No | - | Random seed |

**Response:** `{"usage": {"type": "usd", "usd": N}, "images": [...]}`

---

## POST /generate-with-style-v2

Generate pixel art matching a reference style.

**Sizes:** 16-256px. Output counts: 16px=64, 32px=64, 64px=16, 128px=4, 256px=1

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `description` | string | Yes | - | Text description |
| `style_images` | Base64Image[] | Yes | - | 1-4 style references |
| `style_description` | string | No | - | Style fine-tuning text |
| `image_size` | {width, height} | Yes | - | 16-256px |
| `no_background` | bool | No | - | Transparent background |
| `seed` | int | No | - | Random seed |

**Response:** `{"usage": ..., "images": [...]}`

---

## POST /animate-with-text-v2

Generate animation frames from a reference image and action description.

**Sizes:** 32/64px (16 frames), 128/170/256px (4 frames)

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `reference_image` | Base64Image | Yes | - | Character reference |
| `reference_image_size` | {width, height} | Yes | - | Source dimensions |
| `action` | string | Yes | - | Motion description (max 500 chars) |
| `image_size` | {width, height} | Yes | - | Output frame size |
| `no_background` | bool | No | true | Transparent background |
| `seed` | int | No | - | 0 for random |

**Response:** `{"usage": ..., "images": [...]}`

---

## POST /generate-8-rotations-v2

Generate all 8 directional views of a character.

**Sizes:** 32x32 to 84x84 (square only)

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `method` | string | Yes | - | `rotate_character`, `create_with_style`, or `create_from_concept` |
| `image_size` | {width, height} | Yes | - | 32-84px square |
| `reference_image` | Base64Image | Cond. | - | For rotate_character |
| `description` | string | Cond. | - | For create_with_style |
| `concept_image` | Base64Image | Cond. | - | For create_from_concept |
| `view` | string | No | "low top-down" | `side`, `low top-down`, `high top-down` |

**Response:** `{"usage": ..., "images": {"south": ..., "south-west": ..., "west": ..., "north-west": ..., "north": ..., "north-east": ..., "east": ..., "south-east": ...}}`

---

## POST /inpaint-v3

Edit a masked region of existing pixel art.

**Sizes:** 32x32 to 256x256

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `description` | string | Yes | - | What to generate in mask |
| `inpainting_image` | Base64Image | Yes | - | Image to edit |
| `mask_image` | Base64Image | Yes | - | White=generate, black=keep |
| `context_image` | Base64Image | No | - | Style guidance (up to 1024x1024) |
| `bounding_box` | {x,y,w,h} | No | - | Precise edit area |
| `no_background` | bool | No | - | Transparent background |

**Response:** `{"usage": ..., "images": [...]}`

---

## POST /edit-images-v2

Edit one or more images using text or a reference.

**Frame limits:** 32-64px=16, 65-80px=9, 81-128px=4, 129-256px=1

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `method` | string | Yes | - | `edit_with_text` or `edit_with_reference` |
| `edit_images` | Base64Image[] | Yes | - | Images to edit |
| `image_size` | {width, height} | Yes | - | Output dimensions |
| `description` | string | Cond. | - | For edit_with_text |
| `reference_image` | Base64Image | Cond. | - | For edit_with_reference |
| `no_background` | bool | No | - | Background removal |

**Response:** `{"usage": ..., "images": [...]}`

---

## POST /interpolation-v2

Generate intermediate frames between two keyframes.

**Sizes:** 16x16 to 128x128

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `start_image` | Base64Image | Yes | - | Starting keyframe |
| `end_image` | Base64Image | Yes | - | Ending keyframe |
| `action` | string | Yes | - | Transition description |
| `image_size` | {width, height} | Yes | - | Frame dimensions |
| `no_background` | bool | No | - | Transparent output |
| `seed` | int | No | - | Random seed |

**Response:** `{"usage": ..., "images": [...]}`

---

## POST /edit-animation-v2

Edit existing animation frames.

**Sizes:** 16x16 to 128x128, 2-16 frames

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `description` | string | Yes | - | Edit description (max 500 chars) |
| `frames` | Base64Image[] | Yes | - | 2-16 animation frames |
| `image_size` | {width, height} | Yes | - | Frame dimensions |
| `no_background` | bool | No | - | Transparent frames |
| `seed` | int | No | - | Random seed |

**Response:** `{"usage": ..., "images": [...]}`

---

## POST /transfer-outfit-v2

Transfer an outfit from a reference image to animation frames.

**Sizes:** 16x16 to 128x128, 2-16 frames

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `reference_image` | Base64Image | Yes | - | Outfit reference |
| `frames` | Base64Image[] | Yes | - | 2-16 animation frames |
| `image_size` | {width, height} | Yes | - | Frame dimensions |
| `no_background` | bool | No | - | Transparent output |
| `seed` | int | No | - | Random seed |

**Response:** `{"usage": ..., "images": [...]}`

---

## POST /estimate-skeleton

Extract skeleton keypoints from a character image.

**Sizes:** 16x16, 32x32, 64x64, 128x128, 256x256

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `image` | Base64Image | Yes | Character on transparent background |

**Response:** `{"usage": ..., "keypoints": [{"x": N, "y": N, "label": "...", "z_index": N}, ...]}`

---

## GET /balance

Check account balance and subscription status.

**Response:**
```json
{
  "credits": {"type": "usd", "usd": 0.0},
  "subscription": {"type": "generations", "generations": 1992, "total": 2000}
}
```

# PixelLab API - Complete Endpoint Reference

Base URL: `https://api.pixellab.ai/v1`

Authentication: `Authorization: Bearer YOUR_API_TOKEN`

## Shared Enums

**Outline:** `"single color black outline"` | `"single color outline"` | `"selective outline"` | `"lineless"`

**Shading:** `"flat shading"` | `"basic shading"` | `"medium shading"` | `"detailed shading"` | `"highly detailed shading"`

**Detail:** `"low detail"` | `"medium detail"` | `"highly detailed"`

**CameraView:** `"side"` | `"low top-down"` | `"high top-down"`

**Direction:** `"north"` | `"north-east"` | `"east"` | `"south-east"` | `"south"` | `"south-west"` | `"west"` | `"north-west"`

**SkeletonLabel:** `"NOSE"` | `"NECK"` | `"RIGHT SHOULDER"` | `"RIGHT ELBOW"` | `"RIGHT ARM"` | `"LEFT SHOULDER"` | `"LEFT ELBOW"` | `"LEFT ARM"` | `"RIGHT HIP"` | `"RIGHT KNEE"` | `"RIGHT LEG"` | `"LEFT HIP"` | `"LEFT KNEE"` | `"LEFT LEG"` | `"RIGHT EYE"` | `"LEFT EYE"` | `"RIGHT EAR"` | `"LEFT EAR"`

## Error Codes

| HTTP | Meaning |
|------|---------|
| 200 | Success |
| 401 | Invalid API token |
| 402 | Insufficient credits |
| 422 | Validation error (check parameter ranges) |
| 429 | Too many requests |
| 529 | Rate limit exceeded |

---

## POST /generate-image-pixflux

Text-to-pixel-art generation. Most flexible endpoint.

**Size:** width 16-400, height 16-400, area max 400x400 (160,000 px)

| Parameter | Type | Required | Default | Range | Description |
|-----------|------|----------|---------|-------|-------------|
| `description` | string | Yes | - | - | Text description of the image |
| `image_size.width` | int | Yes | - | 16-400 | Width in pixels |
| `image_size.height` | int | Yes | - | 16-400 | Height in pixels |
| `text_guidance_scale` | float | No | 8.0 | 1.0-20.0 | How closely to follow text |
| `outline` | Outline? | No | null | enum | Outline style (weakly guiding) |
| `shading` | Shading? | No | null | enum | Shading style (weakly guiding) |
| `detail` | Detail? | No | null | enum | Detail level (weakly guiding) |
| `view` | CameraView? | No | null | enum | Camera view angle |
| `direction` | Direction? | No | null | enum | Subject facing direction |
| `isometric` | bool | No | false | - | Isometric view |
| `no_background` | bool | No | false | - | Transparent background (blank bg over 200x200 area) |
| `init_image` | Base64Image? | No | null | - | Starting image |
| `init_image_strength` | int | No | 300 | 1-999 | Init image influence |
| `color_image` | Base64Image? | No | null | - | Forced color palette image |
| `seed` | int? | No | null | - | Random seed |

**Response:**
```json
{
  "usage": {"type": "usd", "usd": 0.005},
  "image": {"type": "base64", "base64": "..."}
}
```

---

## POST /generate-image-bitforge

Style transfer pixel art generation. Use when you have a reference style image.

**Size:** width 16-200, height 16-200, area max 200x200 (40,000 px)

| Parameter | Type | Required | Default | Range | Description |
|-----------|------|----------|---------|-------|-------------|
| `description` | string | Yes | - | - | Text description |
| `image_size.width` | int | Yes | - | 16-200 | Width in pixels |
| `image_size.height` | int | Yes | - | 16-200 | Height in pixels |
| `text_guidance_scale` | float | No | 8.0 | 1.0-20.0 | Text guidance |
| `style_strength` | float | No | 0.0 | 0.0-100.0 | Style transfer strength |
| `outline` | Outline? | No | null | enum | Outline style |
| `shading` | Shading? | No | null | enum | Shading style |
| `detail` | Detail? | No | null | enum | Detail level |
| `view` | CameraView? | No | null | enum | Camera view |
| `direction` | Direction? | No | null | enum | Subject direction |
| `isometric` | bool | No | false | - | Isometric view |
| `oblique_projection` | bool | No | false | - | Oblique projection |
| `no_background` | bool | No | false | - | Transparent background |
| `coverage_percentage` | float? | No | null | 0.0-100.0 | Canvas coverage % |
| `init_image` | Base64Image? | No | null | - | Starting image |
| `init_image_strength` | int | No | 300 | 1-999 | Init image influence |
| `style_image` | Base64Image? | No | null | - | Style reference image |
| `inpainting_image` | Base64Image? | No | null | - | Image to inpaint |
| `mask_image` | Base64Image? | No | null | - | Mask (white=edit) |
| `color_image` | Base64Image? | No | null | - | Forced palette |
| `skeleton_keypoints` | Point[]? | No | null | - | Skeleton points (best at 16/32/64) |
| `skeleton_guidance_scale` | float | No | 1.0 | 0.0-5.0 | Skeleton guidance |
| `seed` | int? | No | null | - | Random seed |

**Response:** Same as pixflux (`usage` + `image`).

---

## POST /animate-with-skeleton

Skeleton-based 4-frame animation. Requires a reference image and skeleton keypoints per frame.

**Size:** Supported: 16x16, 32x32, 64x64, 128x128, 256x256

| Parameter | Type | Required | Default | Range | Description |
|-----------|------|----------|---------|-------|-------------|
| `image_size.width` | int | Yes | - | 16-256 | Width in pixels |
| `image_size.height` | int | Yes | - | 16-256 | Height in pixels |
| `reference_image` | Base64Image | Yes | - | - | Reference character image |
| `skeleton_keypoints` | Point[][] | Yes | - | - | Array of frames, each frame is array of Points |
| `guidance_scale` | float | No | 4.0 | 1.0-20.0 | Overall guidance |
| `view` | CameraView | No | "side" | enum | Camera view |
| `direction` | Direction | No | "east" | enum | Subject direction |
| `isometric` | bool | No | false | - | Isometric view |
| `oblique_projection` | bool | No | false | - | Oblique projection |
| `init_images` | Base64Image[]? | No | null | - | Starting frame images |
| `init_image_strength` | int | No | 300 | 1-999 | Init image influence |
| `inpainting_images` | (Base64Image?)[] | No | [null,null,null] | - | Inpainting reference per frame |
| `mask_images` | (Base64Image?)[] | No | - | - | Masks per frame |
| `color_image` | Base64Image? | No | null | - | Forced palette |
| `seed` | int? | No | null | - | Random seed |

**Point format:**
```json
{"x": 32.0, "y": 16.0, "label": "NOSE", "z_index": 0}
```

**Response:**
```json
{
  "usage": {"type": "usd", "usd": 0.01},
  "images": [
    {"type": "base64", "base64": "..."},
    {"type": "base64", "base64": "..."},
    {"type": "base64", "base64": "..."},
    {"type": "base64", "base64": "..."}
  ]
}
```

---

## POST /animate-with-text

Text-guided animation generation. Fixed 64x64 size. Always generates 4 frames.

**Size:** 64x64 only

| Parameter | Type | Required | Default | Range | Description |
|-----------|------|----------|---------|-------|-------------|
| `image_size.width` | int | Yes | - | 64 only | Must be 64 |
| `image_size.height` | int | Yes | - | 64 only | Must be 64 |
| `description` | string | Yes | - | - | Character description |
| `action` | string | Yes | - | - | Animation action (e.g. "walk", "attack") |
| `reference_image` | Base64Image | Yes | - | - | Reference character image |
| `text_guidance_scale` | float? | No | 8.0 | 1.0-20.0 | Text guidance |
| `image_guidance_scale` | float? | No | 1.4 | 1.0-20.0 | Image guidance |
| `n_frames` | int? | No | 4 | 2-20 | Total animation length |
| `start_frame_index` | int? | No | 0 | 0-20 | Starting frame index |
| `view` | CameraView | No | "side" | enum | Camera view |
| `direction` | Direction | No | "east" | enum | Subject direction |
| `init_images` | Base64Image[]? | No | null | - | Starting frame images |
| `init_image_strength` | int | No | 300 | 1-999 | Init image influence |
| `inpainting_images` | (Base64Image?)[] | No | [null x4] | - | Existing frames to guide |
| `mask_images` | (Base64Image?)[]? | No | [null x4] | - | Masks per frame |
| `color_image` | Base64Image? | No | null | - | Forced palette |
| `seed` | int? | No | 0 | - | Random seed (0=random) |

**Response:** Same as animate-skeleton (`usage` + `images` array).

---

## POST /rotate

Rotate character to a different viewing angle or direction.

**Size:** Supported: 16x16, 32x32, 64x64, 128x128. Width/height 16-200.

| Parameter | Type | Required | Default | Range | Description |
|-----------|------|----------|---------|-------|-------------|
| `image_size.width` | int | Yes | - | 16-200 | Width in pixels |
| `image_size.height` | int | Yes | - | 16-200 | Height in pixels |
| `from_image` | Base64Image | Yes | - | - | Source image to rotate |
| `from_view` | CameraView? | No | "side" | enum | Current view |
| `to_view` | CameraView? | No | "side" | enum | Target view |
| `from_direction` | Direction? | No | "south" | enum | Current direction |
| `to_direction` | Direction? | No | "east" | enum | Target direction |
| `view_change` | int? | No | null | -90 to 90 | Degrees to tilt |
| `direction_change` | int? | No | null | -180 to 180 | Degrees to rotate |
| `isometric` | bool | No | false | - | Isometric view |
| `oblique_projection` | bool | No | false | - | Oblique projection |
| `image_guidance_scale` | float | No | 3.0 | 1.0-20.0 | Image guidance |
| `init_image` | Base64Image? | No | null | - | Starting image |
| `init_image_strength` | int | No | 300 | 1-999 | Init image influence |
| `mask_image` | Base64Image? | No | null | - | Mask (requires init_image) |
| `from_image` | Base64Image | Yes | - | - | Image to rotate from |
| `color_image` | Base64Image? | No | null | - | Forced palette |
| `seed` | int? | No | null | - | Random seed |

**Response:** `usage` + single `image`.

---

## POST /inpaint

Edit a masked region of existing pixel art.

**Size:** width 16-200, height 16-200, area max 200x200

| Parameter | Type | Required | Default | Range | Description |
|-----------|------|----------|---------|-------|-------------|
| `description` | string | Yes | - | - | What to generate in the masked area |
| `image_size.width` | int | Yes | - | 16-200 | Width in pixels |
| `image_size.height` | int | Yes | - | 16-200 | Height in pixels |
| `inpainting_image` | Base64Image | Yes | - | - | Image to edit |
| `mask_image` | Base64Image | Yes | - | - | Mask (white=regenerate, black=keep) |
| `text_guidance_scale` | float | No | 3.0 | 1.0-10.0 | Text guidance |
| `outline` | Outline? | No | null | enum | Outline style |
| `shading` | Shading? | No | null | enum | Shading style |
| `detail` | Detail? | No | null | enum | Detail level |
| `view` | CameraView? | No | null | enum | Camera view |
| `direction` | Direction? | No | null | enum | Subject direction |
| `isometric` | bool | No | false | - | Isometric view |
| `oblique_projection` | bool | No | false | - | Oblique projection |
| `no_background` | bool | No | false | - | Transparent background |
| `init_image` | Base64Image? | No | null | - | Starting image |
| `init_image_strength` | int | No | 300 | 1-999 | Init image influence |
| `color_image` | Base64Image? | No | null | - | Forced palette |
| `seed` | int? | No | null | - | Random seed |

**Response:** `usage` + single `image`.

---

## POST /estimate-skeleton

Extract skeleton keypoints from a character image. Character should be on a transparent background.

**Size:** Supported: 16x16, 32x32, 64x64, 128x128, 256x256

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `image` | Base64Image | Yes | - | Character image (transparent bg) |

**Response:**
```json
{
  "usage": {"type": "usd", "usd": 0.001},
  "keypoints": [
    {"x": 32.0, "y": 10.0, "label": "NOSE", "z_index": 0},
    {"x": 32.0, "y": 16.0, "label": "NECK", "z_index": 0},
    ...
  ]
}
```

---

## GET /balance

Check account credit balance.

**Request:** No body. Only requires Authorization header.

**Response:**
```json
{"type": "usd", "usd": 4.95}
```

**Errors:** Only 401 (invalid token).

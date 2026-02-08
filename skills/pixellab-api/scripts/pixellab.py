#!/usr/bin/env python3
"""PixelLab API helper script for Claude Code.

Unified CLI for all PixelLab pixel art generation endpoints.
Uses only Python stdlib (no pip dependencies).

Usage:
    python3 pixellab.py <subcommand> [options]

Subcommands:
    generate-pixflux    Text-to-pixel-art generation (up to 400x400)
    generate-bitforge   Style transfer pixel art generation (up to 200x200)
    animate-skeleton    Skeleton-based 4-frame animation (up to 256x256)
    animate-text        Text-guided animation (64x64 only)
    rotate              Rotate character view/direction (up to 200x200)
    inpaint             Edit masked region of existing art (up to 200x200)
    estimate-skeleton   Extract skeleton keypoints from character image
    balance             Check account credit balance

Environment:
    PIXELLAB_API_KEY    Required. Your PixelLab API token.
"""

import argparse
import base64
import json
import os
import struct
import sys
import urllib.error
import urllib.request
import zlib

API_BASE = "https://api.pixellab.ai/v1"


def get_api_key():
    key = os.environ.get("PIXELLAB_API_KEY")
    if not key:
        return None, "PIXELLAB_API_KEY environment variable is not set"
    return key, None


def encode_image(path):
    """Read a PNG file and return base64-encoded string."""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")


def decode_image(b64_data, output_path):
    """Decode base64 image data and save as PNG."""
    data = base64.b64decode(b64_data)
    with open(output_path, "wb") as f:
        f.write(data)


def make_base64_image(path):
    """Create a Base64Image object from a file path."""
    return {"type": "base64", "base64": encode_image(path)}


def api_request(method, endpoint, body=None, api_key=None):
    """Make an API request and return parsed JSON response."""
    url = f"{API_BASE}{endpoint}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    if body is not None:
        data = json.dumps(body).encode("utf-8")
    else:
        data = None

    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8")), None
    except urllib.error.HTTPError as e:
        try:
            error_body = json.loads(e.read().decode("utf-8"))
            detail = error_body.get("detail", str(error_body))
        except Exception:
            detail = e.reason
        return None, f"HTTP {e.code}: {detail}"
    except urllib.error.URLError as e:
        return None, f"Connection error: {e.reason}"
    except Exception as e:
        return None, str(e)


def output_success(output_files, cost_usd):
    """Print success JSON to stdout."""
    print(json.dumps({
        "success": True,
        "output_files": output_files,
        "cost_usd": cost_usd,
    }))


def output_error(message):
    """Print error JSON to stdout."""
    print(json.dumps({
        "success": False,
        "error": message,
    }))
    sys.exit(1)


def make_spritesheet(frame_paths, output_path):
    """Combine frame PNGs into a horizontal spritesheet.

    Reads raw PNG data, decodes pixel data, combines horizontally,
    and writes a new PNG. Uses only stdlib (struct, zlib).
    """
    frames = []
    for path in frame_paths:
        with open(path, "rb") as f:
            png_data = f.read()
        w, h, pixels = decode_png_pixels(png_data)
        frames.append((w, h, pixels))

    if not frames:
        return

    frame_w, frame_h = frames[0][0], frames[0][1]
    total_w = frame_w * len(frames)

    # Build combined pixel rows
    rows = []
    for y in range(frame_h):
        row = b"\x00"  # filter byte: None
        for fw, fh, pixels in frames:
            row_start = y * (fw * 4)
            row_end = row_start + fw * 4
            row += pixels[row_start:row_end]
        rows.append(row)

    raw_data = b"".join(rows)
    write_png(output_path, total_w, frame_h, raw_data)


def decode_png_pixels(data):
    """Minimal PNG decoder - returns (width, height, raw_rgba_bytes)."""
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("Not a PNG file")

    pos = 8
    width = height = bit_depth = color_type = 0
    idat_chunks = []

    while pos < len(data):
        chunk_len = struct.unpack(">I", data[pos:pos + 4])[0]
        chunk_type = data[pos + 4:pos + 8]
        chunk_data = data[pos + 8:pos + 8 + chunk_len]
        pos += 12 + chunk_len  # 4 len + 4 type + data + 4 crc

        if chunk_type == b"IHDR":
            width = struct.unpack(">I", chunk_data[0:4])[0]
            height = struct.unpack(">I", chunk_data[4:8])[0]
            bit_depth = chunk_data[8]
            color_type = chunk_data[9]
        elif chunk_type == b"IDAT":
            idat_chunks.append(chunk_data)
        elif chunk_type == b"IEND":
            break

    if color_type not in (2, 6):
        raise ValueError(f"Unsupported color type {color_type} (need RGB or RGBA)")

    raw = zlib.decompress(b"".join(idat_chunks))
    channels = 4 if color_type == 6 else 3
    stride = width * channels

    # Reconstruct pixels with PNG filtering
    pixels = bytearray()
    prev_row = bytearray(stride)

    for y in range(height):
        row_start = y * (stride + 1)
        filter_byte = raw[row_start]
        row_data = bytearray(raw[row_start + 1:row_start + 1 + stride])

        if filter_byte == 1:  # Sub
            for i in range(channels, stride):
                row_data[i] = (row_data[i] + row_data[i - channels]) & 0xFF
        elif filter_byte == 2:  # Up
            for i in range(stride):
                row_data[i] = (row_data[i] + prev_row[i]) & 0xFF
        elif filter_byte == 3:  # Average
            for i in range(stride):
                a = row_data[i - channels] if i >= channels else 0
                row_data[i] = (row_data[i] + (a + prev_row[i]) // 2) & 0xFF
        elif filter_byte == 4:  # Paeth
            for i in range(stride):
                a = row_data[i - channels] if i >= channels else 0
                b = prev_row[i]
                c = prev_row[i - channels] if i >= channels else 0
                row_data[i] = (row_data[i] + paeth_predictor(a, b, c)) & 0xFF

        if color_type == 2:  # RGB -> RGBA
            rgba_row = bytearray()
            for x in range(width):
                rgba_row += row_data[x * 3:x * 3 + 3] + b"\xff"
            pixels += rgba_row
        else:
            pixels += row_data

        prev_row = row_data

    return width, height, bytes(pixels)


def paeth_predictor(a, b, c):
    p = a + b - c
    pa = abs(p - a)
    pb = abs(p - b)
    pc = abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    elif pb <= pc:
        return b
    else:
        return c


def write_png(path, width, height, raw_data):
    """Write a minimal RGBA PNG file."""
    def make_chunk(chunk_type, data):
        chunk = chunk_type + data
        crc = struct.pack(">I", zlib.crc32(chunk) & 0xFFFFFFFF)
        return struct.pack(">I", len(data)) + chunk + crc

    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    compressed = zlib.compress(raw_data)

    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(make_chunk(b"IHDR", ihdr_data))
        f.write(make_chunk(b"IDAT", compressed))
        f.write(make_chunk(b"IEND", b""))


def add_common_style_args(parser):
    """Add common style arguments shared across generation endpoints."""
    parser.add_argument("--outline", choices=[
        "single color black outline", "single color outline",
        "selective outline", "lineless",
    ], default=None, help="Outline style")
    parser.add_argument("--shading", choices=[
        "flat shading", "basic shading", "medium shading",
        "detailed shading", "highly detailed shading",
    ], default=None, help="Shading style")
    parser.add_argument("--detail", choices=[
        "low detail", "medium detail", "highly detailed",
    ], default=None, help="Detail level")
    parser.add_argument("--view", choices=[
        "side", "low top-down", "high top-down",
    ], default=None, help="Camera view angle")
    parser.add_argument("--direction", choices=[
        "north", "north-east", "east", "south-east",
        "south", "south-west", "west", "north-west",
    ], default=None, help="Subject facing direction")


def add_size_args(parser, default_w=64, default_h=64):
    """Add width/height arguments."""
    parser.add_argument("--width", type=int, default=default_w, help="Image width in pixels")
    parser.add_argument("--height", type=int, default=default_h, help="Image height in pixels")


def add_init_image_args(parser):
    """Add init image arguments."""
    parser.add_argument("--init-image", default=None, help="Path to initial image")
    parser.add_argument("--init-image-strength", type=int, default=300,
                        help="Strength of init image (1-999, default 300)")


def add_seed_arg(parser):
    """Add seed argument."""
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")


def build_body_with_optionals(body, args, keys):
    """Add optional fields to request body if they are set."""
    for key in keys:
        attr = key.replace("-", "_")
        val = getattr(args, attr, None)
        if val is not None:
            body[key.replace("-", "_")] = val


# --- Subcommand handlers ---

def cmd_balance(args):
    api_key, err = get_api_key()
    if err:
        output_error(err)

    resp, err = api_request("GET", "/balance", api_key=api_key)
    if err:
        output_error(err)

    print(json.dumps({
        "success": True,
        "balance_usd": resp.get("usd", 0),
        "output_files": [],
        "cost_usd": 0,
    }))


def cmd_generate_pixflux(args):
    api_key, err = get_api_key()
    if err:
        output_error(err)

    body = {
        "description": args.description,
        "image_size": {"width": args.width, "height": args.height},
    }

    if args.no_background:
        body["no_background"] = True
    if args.isometric:
        body["isometric"] = True
    if args.text_guidance_scale is not None:
        body["text_guidance_scale"] = args.text_guidance_scale
    if args.init_image:
        body["init_image"] = make_base64_image(args.init_image)
        body["init_image_strength"] = args.init_image_strength
    if args.color_image:
        body["color_image"] = make_base64_image(args.color_image)

    build_body_with_optionals(body, args, [
        "outline", "shading", "detail", "view", "direction", "seed",
    ])

    resp, err = api_request("POST", "/generate-image-pixflux", body, api_key)
    if err:
        output_error(err)

    output_path = args.output or "output.png"
    decode_image(resp["image"]["base64"], output_path)
    cost = resp.get("usage", {}).get("usd", 0)
    output_success([output_path], cost)


def cmd_generate_bitforge(args):
    api_key, err = get_api_key()
    if err:
        output_error(err)

    body = {
        "description": args.description,
        "image_size": {"width": args.width, "height": args.height},
    }

    if args.no_background:
        body["no_background"] = True
    if args.isometric:
        body["isometric"] = True
    if args.oblique_projection:
        body["oblique_projection"] = True
    if args.text_guidance_scale is not None:
        body["text_guidance_scale"] = args.text_guidance_scale
    if args.style_strength is not None:
        body["style_strength"] = args.style_strength
    if args.coverage_percentage is not None:
        body["coverage_percentage"] = args.coverage_percentage
    if args.init_image:
        body["init_image"] = make_base64_image(args.init_image)
        body["init_image_strength"] = args.init_image_strength
    if args.style_image:
        body["style_image"] = make_base64_image(args.style_image)
    if args.inpainting_image:
        body["inpainting_image"] = make_base64_image(args.inpainting_image)
    if args.mask_image:
        body["mask_image"] = make_base64_image(args.mask_image)
    if args.color_image:
        body["color_image"] = make_base64_image(args.color_image)
    if args.skeleton_keypoints:
        with open(args.skeleton_keypoints) as f:
            body["skeleton_keypoints"] = json.load(f)

    build_body_with_optionals(body, args, [
        "outline", "shading", "detail", "view", "direction", "seed",
    ])

    resp, err = api_request("POST", "/generate-image-bitforge", body, api_key)
    if err:
        output_error(err)

    output_path = args.output or "output.png"
    decode_image(resp["image"]["base64"], output_path)
    cost = resp.get("usage", {}).get("usd", 0)
    output_success([output_path], cost)


def cmd_animate_skeleton(args):
    api_key, err = get_api_key()
    if err:
        output_error(err)

    with open(args.skeleton_keypoints) as f:
        keypoints = json.load(f)

    body = {
        "image_size": {"width": args.width, "height": args.height},
        "reference_image": make_base64_image(args.reference_image),
        "skeleton_keypoints": keypoints,
    }

    if args.view:
        body["view"] = args.view
    if args.direction:
        body["direction"] = args.direction
    if args.isometric:
        body["isometric"] = True
    if args.oblique_projection:
        body["oblique_projection"] = True
    if args.guidance_scale is not None:
        body["guidance_scale"] = args.guidance_scale
    if args.init_images:
        body["init_images"] = [make_base64_image(p) for p in args.init_images]
        body["init_image_strength"] = args.init_image_strength
    if args.color_image:
        body["color_image"] = make_base64_image(args.color_image)
    if args.seed is not None:
        body["seed"] = args.seed

    resp, err = api_request("POST", "/animate-with-skeleton", body, api_key)
    if err:
        output_error(err)

    base = args.output or "frame"
    if base.endswith(".png"):
        base = base[:-4]

    output_files = []
    for i, img in enumerate(resp["images"]):
        path = f"{base}_{i}.png"
        decode_image(img["base64"], path)
        output_files.append(path)

    if args.spritesheet:
        sheet_path = f"{base}_spritesheet.png"
        make_spritesheet(output_files, sheet_path)
        output_files.append(sheet_path)

    cost = resp.get("usage", {}).get("usd", 0)
    output_success(output_files, cost)


def cmd_animate_text(args):
    api_key, err = get_api_key()
    if err:
        output_error(err)

    body = {
        "image_size": {"width": 64, "height": 64},
        "description": args.description,
        "action": args.action,
        "reference_image": make_base64_image(args.reference_image),
    }

    if args.view:
        body["view"] = args.view
    if args.direction:
        body["direction"] = args.direction
    if args.n_frames is not None:
        body["n_frames"] = args.n_frames
    if args.start_frame_index is not None:
        body["start_frame_index"] = args.start_frame_index
    if args.text_guidance_scale is not None:
        body["text_guidance_scale"] = args.text_guidance_scale
    if args.image_guidance_scale is not None:
        body["image_guidance_scale"] = args.image_guidance_scale
    if args.init_images:
        body["init_images"] = [make_base64_image(p) for p in args.init_images]
        body["init_image_strength"] = args.init_image_strength
    if args.color_image:
        body["color_image"] = make_base64_image(args.color_image)
    if args.seed is not None:
        body["seed"] = args.seed

    resp, err = api_request("POST", "/animate-with-text", body, api_key)
    if err:
        output_error(err)

    base = args.output or "frame"
    if base.endswith(".png"):
        base = base[:-4]

    output_files = []
    for i, img in enumerate(resp["images"]):
        path = f"{base}_{i}.png"
        decode_image(img["base64"], path)
        output_files.append(path)

    if args.spritesheet:
        sheet_path = f"{base}_spritesheet.png"
        make_spritesheet(output_files, sheet_path)
        output_files.append(sheet_path)

    cost = resp.get("usage", {}).get("usd", 0)
    output_success(output_files, cost)


def cmd_rotate(args):
    api_key, err = get_api_key()
    if err:
        output_error(err)

    body = {
        "image_size": {"width": args.width, "height": args.height},
        "from_image": make_base64_image(args.from_image),
    }

    if args.from_view:
        body["from_view"] = args.from_view
    if args.to_view:
        body["to_view"] = args.to_view
    if args.from_direction:
        body["from_direction"] = args.from_direction
    if args.to_direction:
        body["to_direction"] = args.to_direction
    if args.view_change is not None:
        body["view_change"] = args.view_change
    if args.direction_change is not None:
        body["direction_change"] = args.direction_change
    if args.isometric:
        body["isometric"] = True
    if args.oblique_projection:
        body["oblique_projection"] = True
    if args.image_guidance_scale is not None:
        body["image_guidance_scale"] = args.image_guidance_scale
    if args.init_image:
        body["init_image"] = make_base64_image(args.init_image)
        body["init_image_strength"] = args.init_image_strength
    if args.mask_image:
        body["mask_image"] = make_base64_image(args.mask_image)
    if args.color_image:
        body["color_image"] = make_base64_image(args.color_image)
    if args.seed is not None:
        body["seed"] = args.seed

    resp, err = api_request("POST", "/rotate", body, api_key)
    if err:
        output_error(err)

    output_path = args.output or "rotated.png"
    decode_image(resp["image"]["base64"], output_path)
    cost = resp.get("usage", {}).get("usd", 0)
    output_success([output_path], cost)


def cmd_inpaint(args):
    api_key, err = get_api_key()
    if err:
        output_error(err)

    body = {
        "description": args.description,
        "image_size": {"width": args.width, "height": args.height},
        "inpainting_image": make_base64_image(args.inpainting_image),
        "mask_image": make_base64_image(args.mask_image),
    }

    if args.no_background:
        body["no_background"] = True
    if args.isometric:
        body["isometric"] = True
    if args.oblique_projection:
        body["oblique_projection"] = True
    if args.text_guidance_scale is not None:
        body["text_guidance_scale"] = args.text_guidance_scale
    if args.init_image:
        body["init_image"] = make_base64_image(args.init_image)
        body["init_image_strength"] = args.init_image_strength
    if args.color_image:
        body["color_image"] = make_base64_image(args.color_image)

    build_body_with_optionals(body, args, [
        "outline", "shading", "detail", "view", "direction", "seed",
    ])

    resp, err = api_request("POST", "/inpaint", body, api_key)
    if err:
        output_error(err)

    output_path = args.output or "inpainted.png"
    decode_image(resp["image"]["base64"], output_path)
    cost = resp.get("usage", {}).get("usd", 0)
    output_success([output_path], cost)


def cmd_estimate_skeleton(args):
    api_key, err = get_api_key()
    if err:
        output_error(err)

    body = {
        "image": make_base64_image(args.image),
    }

    resp, err = api_request("POST", "/estimate-skeleton", body, api_key)
    if err:
        output_error(err)

    keypoints = resp.get("keypoints", [])
    cost = resp.get("usage", {}).get("usd", 0)

    output_files = []
    if args.output:
        with open(args.output, "w") as f:
            json.dump(keypoints, f, indent=2)
        output_files.append(args.output)

    print(json.dumps({
        "success": True,
        "keypoints": keypoints,
        "output_files": output_files,
        "cost_usd": cost,
    }))


# --- Argument parser ---

def build_parser():
    parser = argparse.ArgumentParser(
        description="PixelLab API - pixel art generation CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # balance
    sub.add_parser("balance", help="Check account credit balance")

    # generate-pixflux
    p = sub.add_parser("generate-pixflux", help="Text-to-pixel-art (up to 400x400)")
    p.add_argument("--description", required=True, help="Text description of image")
    add_size_args(p, 64, 64)
    add_common_style_args(p)
    p.add_argument("--no-background", action="store_true", help="Transparent background")
    p.add_argument("--isometric", action="store_true", help="Isometric view")
    p.add_argument("--text-guidance-scale", type=float, default=None,
                   help="Text guidance (1.0-20.0, default 8.0)")
    add_init_image_args(p)
    p.add_argument("--color-image", default=None, help="Path to color palette image")
    add_seed_arg(p)
    p.add_argument("--output", "-o", default=None, help="Output file path (default: output.png)")

    # generate-bitforge
    p = sub.add_parser("generate-bitforge", help="Style transfer pixel art (up to 200x200)")
    p.add_argument("--description", required=True, help="Text description of image")
    add_size_args(p, 64, 64)
    add_common_style_args(p)
    p.add_argument("--no-background", action="store_true", help="Transparent background")
    p.add_argument("--isometric", action="store_true", help="Isometric view")
    p.add_argument("--oblique-projection", action="store_true", help="Oblique projection view")
    p.add_argument("--text-guidance-scale", type=float, default=None,
                   help="Text guidance (1.0-20.0, default 8.0)")
    p.add_argument("--style-strength", type=float, default=None,
                   help="Style transfer strength (0-100)")
    p.add_argument("--coverage-percentage", type=float, default=None,
                   help="Canvas coverage percentage (0-100)")
    add_init_image_args(p)
    p.add_argument("--style-image", default=None, help="Path to style reference image")
    p.add_argument("--inpainting-image", default=None, help="Path to image to inpaint")
    p.add_argument("--mask-image", default=None, help="Path to mask image (white=edit area)")
    p.add_argument("--color-image", default=None, help="Path to color palette image")
    p.add_argument("--skeleton-keypoints", default=None,
                   help="Path to JSON file with skeleton keypoints")
    add_seed_arg(p)
    p.add_argument("--output", "-o", default=None, help="Output file path (default: output.png)")

    # animate-skeleton
    p = sub.add_parser("animate-skeleton", help="Skeleton-based animation (up to 256x256)")
    add_size_args(p, 64, 64)
    p.add_argument("--reference-image", required=True, help="Path to reference character image")
    p.add_argument("--skeleton-keypoints", required=True,
                   help="Path to JSON file with skeleton keypoints (array of frames)")
    p.add_argument("--view", choices=["side", "low top-down", "high top-down"], default=None)
    p.add_argument("--direction", choices=[
        "north", "north-east", "east", "south-east",
        "south", "south-west", "west", "north-west",
    ], default=None)
    p.add_argument("--isometric", action="store_true")
    p.add_argument("--oblique-projection", action="store_true")
    p.add_argument("--guidance-scale", type=float, default=None,
                   help="Guidance scale (1.0-20.0, default 4.0)")
    p.add_argument("--init-images", nargs="+", default=None,
                   help="Paths to initial frame images")
    p.add_argument("--init-image-strength", type=int, default=300)
    p.add_argument("--color-image", default=None, help="Path to color palette image")
    add_seed_arg(p)
    p.add_argument("--spritesheet", action="store_true",
                   help="Also create a horizontal spritesheet")
    p.add_argument("--output", "-o", default=None,
                   help="Output base name (default: frame, produces frame_0.png etc)")

    # animate-text
    p = sub.add_parser("animate-text", help="Text-guided animation (64x64 only)")
    p.add_argument("--description", required=True, help="Character description")
    p.add_argument("--action", required=True, help="Animation action (e.g. 'walk', 'attack')")
    p.add_argument("--reference-image", required=True, help="Path to reference character image")
    p.add_argument("--view", choices=["side", "low top-down", "high top-down"], default=None)
    p.add_argument("--direction", choices=[
        "north", "north-east", "east", "south-east",
        "south", "south-west", "west", "north-west",
    ], default=None)
    p.add_argument("--n-frames", type=int, default=None,
                   help="Total animation frames (2-20, default 4)")
    p.add_argument("--start-frame-index", type=int, default=None,
                   help="Starting frame index (0-20, default 0)")
    p.add_argument("--text-guidance-scale", type=float, default=None,
                   help="Text guidance (1.0-20.0, default 8.0)")
    p.add_argument("--image-guidance-scale", type=float, default=None,
                   help="Image guidance (1.0-20.0, default 1.4)")
    p.add_argument("--init-images", nargs="+", default=None,
                   help="Paths to initial frame images")
    p.add_argument("--init-image-strength", type=int, default=300)
    p.add_argument("--color-image", default=None, help="Path to color palette image")
    add_seed_arg(p)
    p.add_argument("--spritesheet", action="store_true",
                   help="Also create a horizontal spritesheet")
    p.add_argument("--output", "-o", default=None,
                   help="Output base name (default: frame, produces frame_0.png etc)")

    # rotate
    p = sub.add_parser("rotate", help="Rotate character view/direction (up to 200x200)")
    add_size_args(p, 64, 64)
    p.add_argument("--from-image", required=True, help="Path to source image to rotate")
    p.add_argument("--from-view", choices=["side", "low top-down", "high top-down"],
                   default=None, help="Current view (default: side)")
    p.add_argument("--to-view", choices=["side", "low top-down", "high top-down"],
                   default=None, help="Target view (default: side)")
    p.add_argument("--from-direction", choices=[
        "north", "north-east", "east", "south-east",
        "south", "south-west", "west", "north-west",
    ], default=None, help="Current direction (default: south)")
    p.add_argument("--to-direction", choices=[
        "north", "north-east", "east", "south-east",
        "south", "south-west", "west", "north-west",
    ], default=None, help="Target direction (default: east)")
    p.add_argument("--view-change", type=int, default=None,
                   help="Degrees to tilt (-90 to 90)")
    p.add_argument("--direction-change", type=int, default=None,
                   help="Degrees to rotate (-180 to 180)")
    p.add_argument("--isometric", action="store_true")
    p.add_argument("--oblique-projection", action="store_true")
    p.add_argument("--image-guidance-scale", type=float, default=None,
                   help="Image guidance (1.0-20.0, default 3.0)")
    add_init_image_args(p)
    p.add_argument("--mask-image", default=None, help="Path to mask image (requires init-image)")
    p.add_argument("--color-image", default=None, help="Path to color palette image")
    add_seed_arg(p)
    p.add_argument("--output", "-o", default=None,
                   help="Output file path (default: rotated.png)")

    # inpaint
    p = sub.add_parser("inpaint", help="Edit masked region of pixel art (up to 200x200)")
    p.add_argument("--description", required=True, help="Description of what to generate in mask")
    add_size_args(p, 64, 64)
    add_common_style_args(p)
    p.add_argument("--inpainting-image", required=True, help="Path to image to edit")
    p.add_argument("--mask-image", required=True,
                   help="Path to mask image (white=edit area, black=keep)")
    p.add_argument("--no-background", action="store_true", help="Transparent background")
    p.add_argument("--isometric", action="store_true")
    p.add_argument("--oblique-projection", action="store_true")
    p.add_argument("--text-guidance-scale", type=float, default=None,
                   help="Text guidance (1.0-10.0, default 3.0)")
    add_init_image_args(p)
    p.add_argument("--color-image", default=None, help="Path to color palette image")
    add_seed_arg(p)
    p.add_argument("--output", "-o", default=None,
                   help="Output file path (default: inpainted.png)")

    # estimate-skeleton
    p = sub.add_parser("estimate-skeleton", help="Extract skeleton keypoints from character")
    p.add_argument("--image", required=True,
                   help="Path to character image (transparent background)")
    p.add_argument("--output", "-o", default=None,
                   help="Output JSON file for keypoints (also printed to stdout)")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    handlers = {
        "balance": cmd_balance,
        "generate-pixflux": cmd_generate_pixflux,
        "generate-bitforge": cmd_generate_bitforge,
        "animate-skeleton": cmd_animate_skeleton,
        "animate-text": cmd_animate_text,
        "rotate": cmd_rotate,
        "inpaint": cmd_inpaint,
        "estimate-skeleton": cmd_estimate_skeleton,
    }

    handler = handlers.get(args.command)
    if handler:
        try:
            handler(args)
        except FileNotFoundError as e:
            output_error(f"File not found: {e.filename}")
        except json.JSONDecodeError as e:
            output_error(f"Invalid JSON: {e}")
        except Exception as e:
            output_error(str(e))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

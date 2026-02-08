#!/usr/bin/env python3
"""PixelLab API v2 helper script for Claude Code.

Unified CLI for all PixelLab pixel art generation endpoints.
Uses only Python stdlib (no pip dependencies).

Usage:
    python3 pixellab.py <subcommand> [options]

Subcommands:
    generate            Generate pixel art from text (Pro, returns variations)
    generate-with-style Style-guided generation (Pro, requires style images)
    animate             Text-guided animation (Pro, multi-size)
    rotate-8            Generate all 8 directional rotations (Pro)
    inpaint             Edit masked region of existing art (Pro)
    edit                Edit images with text or reference (Pro)
    interpolate         Generate frames between two keyframes (Pro)
    edit-animation      Edit existing animation frames (Pro)
    transfer-outfit     Transfer outfit across animation frames (Pro)
    estimate-skeleton   Extract skeleton keypoints from character
    balance             Check account balance and subscription

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

API_BASE = "https://api.pixellab.ai/v2"


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


def get_png_dimensions(path):
    """Read width and height from a PNG file header."""
    with open(path, "rb") as f:
        header = f.read(24)
        if header[:8] == b'\x89PNG\r\n\x1a\n' and header[12:16] == b'IHDR':
            w = struct.unpack(">I", header[16:20])[0]
            h = struct.unpack(">I", header[20:24])[0]
            return w, h
    return None, None


def make_base64_image(path):
    """Create a Base64Image object from a file path."""
    return {"type": "base64", "base64": encode_image(path)}


def make_style_image(path):
    """Create a style image object with image data and dimensions."""
    w, h = get_png_dimensions(path)
    obj = {"image": make_base64_image(path)}
    if w and h:
        obj["width"] = w
        obj["height"] = h
    return obj


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
        with urllib.request.urlopen(req, timeout=600) as resp:
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


def output_success(output_files, cost_usd, extra=None):
    """Print success JSON to stdout."""
    result = {
        "success": True,
        "output_files": output_files,
        "cost_usd": cost_usd,
    }
    if extra:
        result.update(extra)
    print(json.dumps(result))


def output_error(message):
    """Print error JSON to stdout."""
    print(json.dumps({
        "success": False,
        "error": message,
    }))
    sys.exit(1)


def save_image_array(images, base_path, pick=None):
    """Save an array of base64 images. Returns list of saved file paths.

    If pick is set, saves only that index. Otherwise saves all.
    """
    if base_path.endswith(".png"):
        base_path = base_path[:-4]

    output_files = []
    if pick is not None:
        if pick < 0 or pick >= len(images):
            output_error(f"--pick {pick} out of range (0-{len(images)-1})")
        path = f"{base_path}.png"
        decode_image(images[pick]["base64"], path)
        output_files.append(path)
    elif len(images) == 1:
        path = f"{base_path}.png"
        decode_image(images[0]["base64"], path)
        output_files.append(path)
    else:
        for i, img in enumerate(images):
            path = f"{base_path}_{i}.png"
            decode_image(img["base64"], path)
            output_files.append(path)
    return output_files


def make_spritesheet(frame_paths, output_path):
    """Combine frame PNGs into a horizontal spritesheet."""
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
        pos += 12 + chunk_len

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


def add_size_args(parser, default_w=64, default_h=64):
    parser.add_argument("--width", type=int, default=default_w, help="Image width in pixels")
    parser.add_argument("--height", type=int, default=default_h, help="Image height in pixels")


def add_seed_arg(parser):
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")


def add_pick_arg(parser):
    parser.add_argument("--pick", type=int, default=0,
                        help="Save only the Nth variation (0-indexed). Default: 0 (first). Use -1 for all.")
    parser.add_argument("--all", action="store_true",
                        help="Save all variations instead of just the first")


# --- Subcommand handlers ---

def cmd_balance(args):
    api_key, err = get_api_key()
    if err:
        output_error(err)

    resp, err = api_request("GET", "/balance", api_key=api_key)
    if err:
        output_error(err)

    credits_info = resp.get("credits", {})
    sub_info = resp.get("subscription", {})
    print(json.dumps({
        "success": True,
        "balance_usd": credits_info.get("usd", 0),
        "subscription_generations": sub_info.get("generations", 0),
        "subscription_total": sub_info.get("total", 0),
        "output_files": [],
        "cost_usd": 0,
    }))


def cmd_generate(args):
    api_key, err = get_api_key()
    if err:
        output_error(err)

    body = {
        "description": args.description,
        "image_size": {"width": args.width, "height": args.height},
    }

    if args.no_background:
        body["no_background"] = True
    if args.seed is not None:
        body["seed"] = args.seed
    if args.reference_images:
        body["reference_images"] = [make_base64_image(p) for p in args.reference_images]
    if args.style_image:
        body["style_image"] = make_base64_image(args.style_image)

    resp, err = api_request("POST", "/generate-image-v2", body, api_key)
    if err:
        output_error(err)

    images = resp.get("images", [])
    base = args.output or "output"
    pick = None if args.all else args.pick
    output_files = save_image_array(images, base, pick)
    cost = resp.get("usage", {}).get("usd", 0)
    output_success(output_files, cost, {"total_variations": len(images)})


def cmd_generate_with_style(args):
    api_key, err = get_api_key()
    if err:
        output_error(err)

    body = {
        "description": args.description,
        "style_images": [make_style_image(p) for p in args.style_images],
        "image_size": {"width": args.width, "height": args.height},
    }

    if args.style_description:
        body["style_description"] = args.style_description
    if args.no_background:
        body["no_background"] = True
    if args.seed is not None:
        body["seed"] = args.seed

    resp, err = api_request("POST", "/generate-with-style-v2", body, api_key)
    if err:
        output_error(err)

    images = resp.get("images", [])
    base = args.output or "output"
    pick = None if args.all else args.pick
    output_files = save_image_array(images, base, pick)
    cost = resp.get("usage", {}).get("usd", 0)
    output_success(output_files, cost, {"total_variations": len(images)})


def cmd_animate(args):
    api_key, err = get_api_key()
    if err:
        output_error(err)

    body = {
        "reference_image": make_base64_image(args.reference_image),
        "reference_image_size": {"width": args.ref_width, "height": args.ref_height},
        "action": args.action,
        "image_size": {"width": args.width, "height": args.height},
    }

    if args.no_background is not None:
        body["no_background"] = args.no_background
    if args.seed is not None:
        body["seed"] = args.seed

    resp, err = api_request("POST", "/animate-with-text-v2", body, api_key)
    if err:
        output_error(err)

    images = resp.get("images", [])
    base = args.output or "frame"
    output_files = save_image_array(images, base)
    cost = resp.get("usage", {}).get("usd", 0)

    if args.spritesheet and len(output_files) > 1:
        sheet_base = base if not base.endswith(".png") else base[:-4]
        sheet_path = f"{sheet_base}_spritesheet.png"
        make_spritesheet(output_files, sheet_path)
        output_files.append(sheet_path)

    output_success(output_files, cost, {"frame_count": len(images)})


def cmd_rotate_8(args):
    api_key, err = get_api_key()
    if err:
        output_error(err)

    body = {
        "method": args.method,
        "image_size": {"width": args.width, "height": args.height},
    }

    if args.method == "rotate_character" and args.reference_image:
        body["reference_image"] = make_base64_image(args.reference_image)
    if args.method == "create_with_style" and args.description:
        body["description"] = args.description
    if args.method == "create_from_concept" and args.concept_image:
        body["concept_image"] = make_base64_image(args.concept_image)
    if args.view:
        body["view"] = args.view

    resp, err = api_request("POST", "/generate-8-rotations-v2", body, api_key)
    if err:
        output_error(err)

    # Response has images dict keyed by direction: S, SW, W, NW, N, NE, E, SE
    images = resp.get("images", {})
    base = args.output or "rotation"
    if base.endswith(".png"):
        base = base[:-4]

    directions = ["south", "south-west", "west", "north-west",
                   "north", "north-east", "east", "south-east"]
    output_files = []
    for direction in directions:
        img_data = images.get(direction)
        if img_data:
            path = f"{base}_{direction}.png"
            decode_image(img_data["base64"], path)
            output_files.append(path)

    cost = resp.get("usage", {}).get("usd", 0)
    output_success(output_files, cost)


def cmd_inpaint(args):
    api_key, err = get_api_key()
    if err:
        output_error(err)

    body = {
        "description": args.description,
        "inpainting_image": make_base64_image(args.inpainting_image),
        "mask_image": make_base64_image(args.mask_image),
    }

    if args.context_image:
        body["context_image"] = make_base64_image(args.context_image)
    if args.no_background:
        body["no_background"] = True

    resp, err = api_request("POST", "/inpaint-v3", body, api_key)
    if err:
        output_error(err)

    images = resp.get("images", [resp.get("image")])
    if images and images[0] is None:
        images = []
    base = args.output or "inpainted"
    pick = None if args.all else args.pick
    output_files = save_image_array(images, base, pick)
    cost = resp.get("usage", {}).get("usd", 0)
    output_success(output_files, cost)


def cmd_edit(args):
    api_key, err = get_api_key()
    if err:
        output_error(err)

    body = {
        "method": args.method,
        "edit_images": [make_base64_image(p) for p in args.edit_images],
        "image_size": {"width": args.width, "height": args.height},
    }

    if args.method == "edit_with_text" and args.description:
        body["description"] = args.description
    if args.method == "edit_with_reference" and args.reference_image:
        body["reference_image"] = make_base64_image(args.reference_image)
    if args.no_background:
        body["no_background"] = True

    resp, err = api_request("POST", "/edit-images-v2", body, api_key)
    if err:
        output_error(err)

    images = resp.get("images", [])
    base = args.output or "edited"
    output_files = save_image_array(images, base)
    cost = resp.get("usage", {}).get("usd", 0)
    output_success(output_files, cost)


def cmd_interpolate(args):
    api_key, err = get_api_key()
    if err:
        output_error(err)

    body = {
        "start_image": make_base64_image(args.start_image),
        "end_image": make_base64_image(args.end_image),
        "action": args.action,
        "image_size": {"width": args.width, "height": args.height},
    }

    if args.no_background:
        body["no_background"] = True
    if args.seed is not None:
        body["seed"] = args.seed

    resp, err = api_request("POST", "/interpolation-v2", body, api_key)
    if err:
        output_error(err)

    images = resp.get("images", [])
    base = args.output or "interp"
    output_files = save_image_array(images, base)
    cost = resp.get("usage", {}).get("usd", 0)

    if args.spritesheet and len(output_files) > 1:
        sheet_base = base if not base.endswith(".png") else base[:-4]
        sheet_path = f"{sheet_base}_spritesheet.png"
        make_spritesheet(output_files, sheet_path)
        output_files.append(sheet_path)

    output_success(output_files, cost, {"frame_count": len(images)})


def cmd_edit_animation(args):
    api_key, err = get_api_key()
    if err:
        output_error(err)

    body = {
        "description": args.description,
        "frames": [make_base64_image(p) for p in args.frames],
        "image_size": {"width": args.width, "height": args.height},
    }

    if args.no_background:
        body["no_background"] = True
    if args.seed is not None:
        body["seed"] = args.seed

    resp, err = api_request("POST", "/edit-animation-v2", body, api_key)
    if err:
        output_error(err)

    images = resp.get("images", [])
    base = args.output or "edited_frame"
    output_files = save_image_array(images, base)
    cost = resp.get("usage", {}).get("usd", 0)

    if args.spritesheet and len(output_files) > 1:
        sheet_base = base if not base.endswith(".png") else base[:-4]
        sheet_path = f"{sheet_base}_spritesheet.png"
        make_spritesheet(output_files, sheet_path)
        output_files.append(sheet_path)

    output_success(output_files, cost)


def cmd_transfer_outfit(args):
    api_key, err = get_api_key()
    if err:
        output_error(err)

    body = {
        "reference_image": make_base64_image(args.reference_image),
        "frames": [make_base64_image(p) for p in args.frames],
        "image_size": {"width": args.width, "height": args.height},
    }

    if args.no_background:
        body["no_background"] = True
    if args.seed is not None:
        body["seed"] = args.seed

    resp, err = api_request("POST", "/transfer-outfit-v2", body, api_key)
    if err:
        output_error(err)

    images = resp.get("images", [])
    base = args.output or "outfit_frame"
    output_files = save_image_array(images, base)
    cost = resp.get("usage", {}).get("usd", 0)

    if args.spritesheet and len(output_files) > 1:
        sheet_base = base if not base.endswith(".png") else base[:-4]
        sheet_path = f"{sheet_base}_spritesheet.png"
        make_spritesheet(output_files, sheet_path)
        output_files.append(sheet_path)

    output_success(output_files, cost)


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
        description="PixelLab API v2 - pixel art generation CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # balance
    sub.add_parser("balance", help="Check account balance and subscription")

    # generate
    p = sub.add_parser("generate", help="Generate pixel art from text (Pro)")
    p.add_argument("--description", required=True, help="Text description of image")
    add_size_args(p, 64, 64)
    p.add_argument("--no-background", action="store_true", help="Transparent background")
    p.add_argument("--reference-images", nargs="+", default=None,
                   help="Paths to up to 4 reference images for guidance")
    p.add_argument("--style-image", default=None, help="Path to style reference image")
    add_seed_arg(p)
    add_pick_arg(p)
    p.add_argument("--output", "-o", default=None, help="Output path (default: output)")

    # generate-with-style
    p = sub.add_parser("generate-with-style", help="Style-guided generation (Pro)")
    p.add_argument("--description", required=True, help="Text description of image")
    p.add_argument("--style-images", nargs="+", required=True,
                   help="Paths to 1-4 style reference images")
    p.add_argument("--style-description", default=None, help="Description of the style")
    add_size_args(p, 64, 64)
    p.add_argument("--no-background", action="store_true", help="Transparent background")
    add_seed_arg(p)
    add_pick_arg(p)
    p.add_argument("--output", "-o", default=None, help="Output path (default: output)")

    # animate
    p = sub.add_parser("animate", help="Text-guided animation (Pro)")
    p.add_argument("--reference-image", required=True, help="Path to reference character image")
    p.add_argument("--ref-width", type=int, required=True,
                   help="Width of reference image in pixels")
    p.add_argument("--ref-height", type=int, required=True,
                   help="Height of reference image in pixels")
    p.add_argument("--action", required=True, help="Animation action (e.g. 'walk', 'attack')")
    add_size_args(p, 64, 64)
    p.add_argument("--no-background", action="store_true", default=None,
                   help="Transparent background (default: true)")
    add_seed_arg(p)
    p.add_argument("--spritesheet", action="store_true",
                   help="Also create a horizontal spritesheet")
    p.add_argument("--output", "-o", default=None,
                   help="Output base name (default: frame)")

    # rotate-8
    p = sub.add_parser("rotate-8", help="Generate 8 directional rotations (Pro)")
    p.add_argument("--method", required=True,
                   choices=["rotate_character", "create_with_style", "create_from_concept"],
                   help="Rotation method")
    add_size_args(p, 64, 64)
    p.add_argument("--reference-image", default=None,
                   help="Path to character image (for rotate_character)")
    p.add_argument("--description", default=None,
                   help="Text description (for create_with_style)")
    p.add_argument("--concept-image", default=None,
                   help="Path to concept image (for create_from_concept)")
    p.add_argument("--view", choices=["side", "low top-down", "high top-down"],
                   default=None, help="Camera view angle")
    p.add_argument("--output", "-o", default=None,
                   help="Output base name (default: rotation)")

    # inpaint
    p = sub.add_parser("inpaint", help="Edit masked region of pixel art (Pro)")
    p.add_argument("--description", required=True,
                   help="Description of what to generate in mask")
    p.add_argument("--inpainting-image", required=True, help="Path to image to edit")
    p.add_argument("--mask-image", required=True,
                   help="Path to mask (white=regenerate, black=keep)")
    p.add_argument("--context-image", default=None,
                   help="Path to style guidance image (up to 1024x1024)")
    p.add_argument("--no-background", action="store_true", help="Transparent background")
    add_pick_arg(p)
    p.add_argument("--output", "-o", default=None, help="Output path (default: inpainted)")

    # edit
    p = sub.add_parser("edit", help="Edit images with text or reference (Pro)")
    p.add_argument("--method", required=True,
                   choices=["edit_with_text", "edit_with_reference"],
                   help="Edit method")
    p.add_argument("--edit-images", nargs="+", required=True,
                   help="Paths to images to edit")
    add_size_args(p, 64, 64)
    p.add_argument("--description", default=None,
                   help="Edit description (for edit_with_text)")
    p.add_argument("--reference-image", default=None,
                   help="Path to reference image (for edit_with_reference)")
    p.add_argument("--no-background", action="store_true", help="Transparent background")
    p.add_argument("--output", "-o", default=None, help="Output base name (default: edited)")

    # interpolate
    p = sub.add_parser("interpolate",
                       help="Generate frames between two keyframes (Pro)")
    p.add_argument("--start-image", required=True, help="Path to starting keyframe")
    p.add_argument("--end-image", required=True, help="Path to ending keyframe")
    p.add_argument("--action", required=True, help="Transition description")
    add_size_args(p, 64, 64)
    p.add_argument("--no-background", action="store_true", help="Transparent background")
    add_seed_arg(p)
    p.add_argument("--spritesheet", action="store_true",
                   help="Also create a horizontal spritesheet")
    p.add_argument("--output", "-o", default=None,
                   help="Output base name (default: interp)")

    # edit-animation
    p = sub.add_parser("edit-animation", help="Edit existing animation frames (Pro)")
    p.add_argument("--description", required=True, help="Edit description")
    p.add_argument("--frames", nargs="+", required=True,
                   help="Paths to 2-16 animation frame images")
    add_size_args(p, 64, 64)
    p.add_argument("--no-background", action="store_true", help="Transparent background")
    add_seed_arg(p)
    p.add_argument("--spritesheet", action="store_true",
                   help="Also create a horizontal spritesheet")
    p.add_argument("--output", "-o", default=None,
                   help="Output base name (default: edited_frame)")

    # transfer-outfit
    p = sub.add_parser("transfer-outfit",
                       help="Transfer outfit across animation frames (Pro)")
    p.add_argument("--reference-image", required=True,
                   help="Path to outfit reference image")
    p.add_argument("--frames", nargs="+", required=True,
                   help="Paths to 2-16 animation frame images")
    add_size_args(p, 64, 64)
    p.add_argument("--no-background", action="store_true", help="Transparent background")
    add_seed_arg(p)
    p.add_argument("--spritesheet", action="store_true",
                   help="Also create a horizontal spritesheet")
    p.add_argument("--output", "-o", default=None,
                   help="Output base name (default: outfit_frame)")

    # estimate-skeleton
    p = sub.add_parser("estimate-skeleton",
                       help="Extract skeleton keypoints from character")
    p.add_argument("--image", required=True,
                   help="Path to character image (transparent background)")
    p.add_argument("--output", "-o", default=None,
                   help="Output JSON file for keypoints")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    handlers = {
        "balance": cmd_balance,
        "generate": cmd_generate,
        "generate-with-style": cmd_generate_with_style,
        "animate": cmd_animate,
        "rotate-8": cmd_rotate_8,
        "inpaint": cmd_inpaint,
        "edit": cmd_edit,
        "interpolate": cmd_interpolate,
        "edit-animation": cmd_edit_animation,
        "transfer-outfit": cmd_transfer_outfit,
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

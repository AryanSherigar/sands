"""Automated 2D Mesh Avatar Builder and Packager.

Portions of rig calculation and layer packaging logic are adapted from
Mesh Avatar Studio (https://github.com/shinshin86/mesh-avatar-studio),
Copyright (c) 2026 Yuki Shindo, licensed under the MIT License.
"""

from __future__ import annotations

import base64
import binascii
import io
import json
import zipfile
from dataclasses import dataclass
from typing import Any

from PIL import Image, ImageDraw, ImageFilter

MAX_AVATAR_IMAGE_BYTES = 5 * 1024 * 1024
MAX_AVATAR_IMAGE_PIXELS = 16_000_000
AVATAR_IMAGE_FORMATS = {"image/png": "PNG", "image/jpeg": "JPEG", "image/webp": "WEBP"}

# NOTE: vertical feature positions as a fraction of image height, calibrated against
# Muse Image portraits (eyes 38-45%, mouth 57-64% down). Keep in step with
# FRAMING_DIRECTIVE in avatar_prompt_service, which asks the model for this framing.
EYE_LINE = 0.42
BROW_LINE = 0.36
NOSE_LINE = 0.53
MOUTH_LINE = 0.61
CHEEK_LINE = 0.54
JAW_LINE = 0.69
HEAD_CENTER_LINE = 0.41


@dataclass(frozen=True)
class FeatureLines:
    """Vertical feature positions as fractions of image height."""

    eye: float = EYE_LINE
    brow: float = BROW_LINE
    nose: float = NOSE_LINE
    mouth: float = MOUTH_LINE
    cheek: float = CHEEK_LINE
    jaw: float = JAW_LINE
    head_center: float = HEAD_CENTER_LINE

    @classmethod
    def calibrated(cls, eye: float, mouth: float) -> FeatureLines:
        """Move the whole face with a measured eye and mouth line, so curated
        portraits that sit off the defaults still get a consistent rig."""
        eye_shift = eye - EYE_LINE
        mouth_shift = mouth - MOUTH_LINE
        middle_shift = (eye_shift + mouth_shift) / 2
        return cls(
            eye=eye,
            brow=BROW_LINE + eye_shift,
            nose=NOSE_LINE + middle_shift,
            mouth=mouth,
            cheek=CHEEK_LINE + middle_shift,
            jaw=JAW_LINE + mouth_shift,
            head_center=HEAD_CENTER_LINE + middle_shift,
        )


def decode_avatar_image(image_url: str) -> bytes:
    header, separator, encoded = image_url.partition(",")
    if (
        not separator
        or not header.startswith("data:")
        or not header.endswith(";base64")
    ):
        raise ValueError("Select a PNG, JPEG or WebP image.")
    image_type = header[5:-7]
    if (
        image_type not in AVATAR_IMAGE_FORMATS
        or len(encoded) > ((MAX_AVATAR_IMAGE_BYTES + 2) // 3) * 4
    ):
        raise ValueError("Unsupported image type or image exceeds 5 MB.")
    try:
        image_bytes = base64.b64decode(encoded, validate=True)
        if not image_bytes or len(image_bytes) > MAX_AVATAR_IMAGE_BYTES:
            raise ValueError("Image is empty or exceeds 5 MB.")
        with Image.open(io.BytesIO(image_bytes)) as image:
            if (
                image.format != AVATAR_IMAGE_FORMATS[image_type]
                or image.width * image.height > MAX_AVATAR_IMAGE_PIXELS
            ):
                raise ValueError("Image format or dimensions are invalid.")
            image.verify()
        return image_bytes
    except (binascii.Error, OSError, Image.DecompressionBombError) as exc:
        raise ValueError("Image could not be decoded.") from exc


def validate_avatar_manifest(manifest: dict[str, Any]) -> bool:
    """Validates that a manifest dictionary matches the mesh-avatar v1 specification."""
    return (
        manifest.get("format") == "mesh-avatar"
        and manifest.get("version") == 1
        and bool(manifest.get("name"))
    )


def _ellipse(cx: float, cy: float, rx: float, ry: float) -> dict[str, float]:
    return {"cx": cx, "cy": cy, "rx": rx, "ry": ry}


def _eye(cx: float, cy: float, width: int, height: int) -> dict[str, object]:
    rx, ry = width * 0.07, height * 0.025
    opening = [[cx - rx, cy], [cx, cy - ry], [cx + rx, cy], [cx, cy + ry]]
    roi = [
        [cx - rx, cy - ry],
        [cx + rx, cy - ry],
        [cx + rx, cy + ry],
        [cx - rx, cy + ry],
    ]
    top = [cy - ry] * 24
    bot = [cy + ry] * 24
    return {
        "opening": opening,
        "roi": roi,
        "x0": cx - rx,
        "x1": cx + rx,
        "top": top,
        "bot": bot,
    }


DEFAULT_FEATURE_LINES = FeatureLines()


def generate_default_rig(
    width: int, height: int, lines: FeatureLines = DEFAULT_FEATURE_LINES
) -> dict[str, Any]:
    cx, cy = width * 0.5, height * lines.eye
    eyes = [
        _eye(width * 0.38, cy, width, height),
        _eye(width * 0.62, cy, width, height),
    ]
    face = {
        "nose": _ellipse(cx, height * lines.nose, width * 0.06, height * 0.06),
        "mouth": _ellipse(cx, height * lines.mouth, width * 0.09, height * 0.04),
        "eyeA": _ellipse(width * 0.38, cy, width * 0.08, height * 0.04),
        "eyeB": _ellipse(width * 0.62, cy, width * 0.08, height * 0.04),
        "earL": _ellipse(width * 0.22, cy, width * 0.05, height * 0.07),
        "earR": _ellipse(width * 0.78, cy, width * 0.05, height * 0.07),
        "brow": {
            **_ellipse(cx, height * lines.brow, width * 0.24, height * 0.03),
            "band": [height * (lines.brow - 0.02), height * (lines.brow + 0.02)],
        },
        "jaw": {
            **_ellipse(cx, height * lines.jaw, width * 0.18, height * 0.08),
            "band": [height * (lines.jaw - 0.04), height * (lines.jaw + 0.04)],
        },
    }
    cell = max(1, min(width, height) // 60)
    return {
        "version": 1,
        "image": {"width": width, "height": height},
        "head": {
            **_ellipse(cx, height * lines.head_center, width * 0.34, height * 0.36),
            "shiftX": width * 0.02,
            "shiftY": height * 0.02,
            "pivotX": cx,
            "pivotY": height * 0.7,
            "maxRoll": 0.05,
            "weightBand": [height * 0.6, height * 0.8],
            "turnBand": [height * 0.6, height * 0.85],
        },
        "body": {
            "pivotX": cx,
            "pivotY": height,
            "maxRoll": 0.02,
            "breathBand": [height * 0.65, height],
            "rollBand": [height * 0.65, height],
            "chest": _ellipse(cx, height * 0.8, width * 0.3, height * 0.15),
            "shoulders": [],
        },
        "face": face,
        "eyes": eyes,
        "mouth": {
            "cx": cx,
            "cy": height * lines.mouth,
            "angle": 0,
            "halfLen": width * 0.05,
            "bow": 0,
            "area": {
                **_ellipse(cx, height * lines.mouth, width * 0.09, height * 0.04),
                "angle": 0,
            },
        },
        "cheeks": [
            [width * 0.3, height * lines.cheek],
            [width * 0.7, height * lines.cheek],
        ],
        "mesh": {
            "baseCell": cell,
            "fine": {"x0": 0, "x1": width, "y0": 0, "y1": height, "cell": cell},
            "handCell": cell,
            "tasselCell": cell,
            "eyeBallCell": cell,
            "eyeCell": cell,
            "spriteCell": cell,
        },
        "view": {"padTop": 0, "padSide": 0, "gazeCenter": [cx, cy]},
    }


def _build_eye_layers(
    img: Image.Image, rig: dict[str, Any], layers: dict[str, Any]
) -> tuple[Image.Image, dict[str, bytes]]:
    width, height = img.size
    eye_images: dict[str, bytes] = {}
    base = img.copy()
    for index in range(2):
        for part in ("ball", "low", "crease", "lash"):
            layers["layers"][f"eye{index}_{part}"] = [0, 0, 1, 1]
        eye = rig["eyes"][index]
        left = max(0, min(width - 1, int(eye["x0"])))
        right = min(width, max(left + 1, int(eye["x1"]) + 1))
        top = max(0, min(height - 1, int(min(eye["top"]))))
        bottom = min(height, max(top + 1, int(max(eye["bot"])) + 1))
        eye_image = img.crop((left, top, right, bottom))
        mask = Image.new("L", eye_image.size, 0)
        ImageDraw.Draw(mask).ellipse(
            (0, 0, eye_image.width - 1, eye_image.height - 1), fill=255
        )
        mask = mask.filter(ImageFilter.GaussianBlur(max(0.5, eye_image.height / 12)))
        eye_image.putalpha(
            Image.composite(
                eye_image.getchannel("A"), Image.new("L", eye_image.size), mask
            )
        )
        eye_buf = io.BytesIO()
        eye_image.save(eye_buf, format="PNG")
        key = f"eye{index}_ball"
        eye_images[key] = eye_buf.getvalue()
        layers["layers"][key] = [left, top, right - left, bottom - top]
        # Approximate closed eyelid from the skin immediately above the eye.
        sample_y = max(0, top - max(1, eye_image.height // 2))
        lid = img.crop((left, sample_y, right, sample_y + 1)).resize(eye_image.size)
        base.paste(lid, (left, top), mask)

    return base, eye_images


def build_mesh_avatar_package(
    image_bytes: bytes, name: str, lines: FeatureLines = DEFAULT_FEATURE_LINES
) -> bytes:
    """Builds an uncompressed .mavatar ZIP archive compliant with mesh-avatar v1."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    width, height = img.size

    manifest = {
        "format": "mesh-avatar",
        "version": 1,
        "name": name,
        "author": "Sands Scenario Studio",
        "studio": {"version": "0.1.0"},
        "lipSync": {"granularity": 0.5, "openness": 0.5, "closeSpeed": 0.5},
    }

    rig = generate_default_rig(width, height, lines)

    layers = {
        "version": 1,
        "build": "sands-generic-v1",
        "size": [width, height],
        "layers": {},
        "eyes": [
            {key: eye[key] for key in ("x0", "x1", "top", "bot")} for eye in rig["eyes"]
        ],
    }
    transparent = io.BytesIO()
    Image.new("RGBA", (1, 1), color=(0, 0, 0, 0)).save(transparent, format="PNG")
    base, eye_images = _build_eye_layers(img, rig, layers)

    # Red-channel hairmask (default full opacity red for hair contour regions)
    hairmask = Image.new("RGBA", (width, height), color=(0, 0, 0, 255))
    hairmask_buf = io.BytesIO()
    hairmask.save(hairmask_buf, format="PNG")

    base_buf = io.BytesIO()
    base.save(base_buf, format="PNG")

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", compression=zipfile.ZIP_STORED) as zf:
        zf.writestr("avatar.json", json.dumps(manifest, indent=2))
        zf.writestr("rig.json", json.dumps(rig, indent=2))
        zf.writestr("built/layers.json", json.dumps(layers, indent=2))
        zf.writestr("built/base.png", base_buf.getvalue())
        zf.writestr("built/hairmask.png", hairmask_buf.getvalue())
        for layer in layers["layers"]:
            zf.writestr(
                f"built/{layer}.png", eye_images.get(layer, transparent.getvalue())
            )

    return zip_buffer.getvalue()

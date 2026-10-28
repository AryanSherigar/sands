"""Automated 2D Mesh Avatar Builder and Packager.

Portions of rig calculation and layer packaging logic are adapted from
Mesh Avatar Studio (https://github.com/shinshin86/mesh-avatar-studio),
Copyright (c) 2026 Yuki Shindo, licensed under the MIT License.
"""

from __future__ import annotations

import io
import json
import zipfile
from typing import Any
from PIL import Image


def validate_avatar_manifest(manifest: dict[str, Any]) -> bool:
    """Validates that a manifest dictionary matches the mesh-avatar v1 specification."""
    return (
        manifest.get("format") == "mesh-avatar"
        and manifest.get("version") == 1
        and bool(manifest.get("name"))
    )


def generate_default_rig(width: int, height: int) -> dict[str, Any]:
    """Generates standard Live2D / Mesh Avatar rigging parameters scaled to image dimensions."""
    cx = width / 2.0
    cy = height * 0.42

    return {
        "version": 1,
        "image": {"width": width, "height": height},
        "head": {
            "center": [cx, cy],
            "rx": width * 0.35,
            "ry": height * 0.4,
            "angle": 0,
            "pivot": [cx, height * 0.75],
            "weightBand": [height * 0.65, height * 0.85],
        },
        "eyes": [
            {
                "center": [cx - width * 0.14, cy - height * 0.04],
                "rx": width * 0.08,
                "ry": height * 0.06,
                "opening": [
                    [cx - width * 0.2, cy - height * 0.04],
                    [cx - width * 0.14, cy - height * 0.07],
                    [cx - width * 0.08, cy - height * 0.04],
                    [cx - width * 0.14, cy - height * 0.01],
                ],
                "roi": [
                    [cx - width * 0.22, cy - height * 0.08],
                    [cx - width * 0.06, cy - height * 0.08],
                    [cx - width * 0.06, cy],
                    [cx - width * 0.22, cy],
                ],
            },
            {
                "center": [cx + width * 0.14, cy - height * 0.04],
                "rx": width * 0.08,
                "ry": height * 0.06,
                "opening": [
                    [cx + width * 0.08, cy - height * 0.04],
                    [cx + width * 0.14, cy - height * 0.07],
                    [cx + width * 0.2, cy - height * 0.04],
                    [cx + width * 0.14, cy - height * 0.01],
                ],
                "roi": [
                    [cx + width * 0.06, cy - height * 0.08],
                    [cx + width * 0.22, cy - height * 0.08],
                    [cx + width * 0.22, cy],
                    [cx + width * 0.06, cy],
                ],
            },
        ],
        "mouth": {
            "center": [cx, cy + height * 0.18],
            "angle": 0,
            "halfLength": width * 0.08,
            "area": {"rx": width * 0.12, "ry": height * 0.08},
        },
        "body": {
            "center": [cx, height * 0.85],
            "rx": width * 0.45,
            "ry": height * 0.2,
            "breathBand": [height * 0.6, height],
        },
        "mesh": {"fine": [0, 0, width, height]},
    }


def build_mesh_avatar_package(image_bytes: bytes, name: str) -> bytes:
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

    rig = generate_default_rig(width, height)

    layers = {
        "version": 1,
        "image": {"width": width, "height": height},
        "layers": [],
    }

    # Red-channel hairmask (default full opacity red for hair contour regions)
    hairmask = Image.new("RGBA", (width, height), color=(255, 0, 0, 255))
    hairmask_buf = io.BytesIO()
    hairmask.save(hairmask_buf, format="PNG")

    base_buf = io.BytesIO()
    img.save(base_buf, format="PNG")

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", compression=zipfile.ZIP_STORED) as zf:
        zf.writestr("avatar.json", json.dumps(manifest, indent=2))
        zf.writestr("rig.json", json.dumps(rig, indent=2))
        zf.writestr("built/layers.json", json.dumps(layers, indent=2))
        zf.writestr("built/base.png", base_buf.getvalue())
        zf.writestr("built/hairmask.png", hairmask_buf.getvalue())

    return zip_buffer.getvalue()

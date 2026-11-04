import base64
import io
import json
import zipfile
from unittest.mock import AsyncMock

import pytest
from app.routers.studio_avatar_router import BuildMeshRequest, build_mesh_endpoint
from app.services.avatar_mesh_builder import (
    EYE_LINE,
    MOUTH_LINE,
    FeatureLines,
    build_mesh_avatar_package,
    decode_avatar_image,
    generate_default_rig,
    validate_avatar_manifest,
)
from fastapi import HTTPException
from PIL import Image


def test_decode_avatar_image_accepts_real_png():
    encoded = base64.b64encode(_create_test_image()).decode()
    assert (
        decode_avatar_image(f"data:image/png;base64,{encoded}") == _create_test_image()
    )


@pytest.mark.parametrize(
    "image",
    [
        "http://127.0.0.1/internal",
        "/avatars/mira.mavatar",
        "data:image/png;base64,invalid!",
        "data:image/png;base64,aGVsbG8=",
        "data:image/svg+xml;base64,PHN2Zz4=",
    ],
)
def test_decode_avatar_image_rejects_unusable_or_remote_input(image):
    with pytest.raises(ValueError):
        decode_avatar_image(image)


@pytest.mark.asyncio
async def test_build_mesh_endpoint_uses_selected_image_and_rejects_remote(monkeypatch):
    upload = AsyncMock(
        side_effect=[
            "https://example.com/avatar.mavatar",
            "https://example.com/avatar.png",
        ]
    )
    monkeypatch.setattr(
        "app.routers.studio_avatar_router.storage_client.upload_public_bytes", upload
    )
    encoded = base64.b64encode(_create_test_image()).decode()
    result = await build_mesh_endpoint(
        BuildMeshRequest(name="Mira", image_url=f"data:image/png;base64,{encoded}"),
        None,
    )
    assert result.avatar_url == "https://example.com/avatar.mavatar"
    assert upload.await_count == 2
    base_image = upload.await_args_list[1].args[1]
    with (
        Image.open(io.BytesIO(base_image)) as actual,
        Image.open(io.BytesIO(_create_test_image())) as expected,
    ):
        assert actual.tobytes() == expected.tobytes()
    with pytest.raises(HTTPException) as exc:
        await build_mesh_endpoint(
            BuildMeshRequest(name="Mira", image_url="http://127.0.0.1/private"), None
        )
    assert exc.value.status_code == 422
    assert upload.await_count == 2
    assert result.portrait_url == "https://example.com/avatar.png"


@pytest.mark.asyncio
async def test_failed_still_upload_removes_generated_mesh(monkeypatch):
    upload = AsyncMock(
        side_effect=[
            "https://example.com/avatar.mavatar",
            OSError("storage unavailable"),
        ]
    )
    delete = AsyncMock()
    monkeypatch.setattr(
        "app.routers.studio_avatar_router.storage_client.upload_public_bytes", upload
    )
    monkeypatch.setattr(
        "app.routers.studio_avatar_router.storage_client.delete_object", delete
    )
    encoded = base64.b64encode(_create_test_image()).decode()
    with pytest.raises(OSError):
        await build_mesh_endpoint(
            BuildMeshRequest(name="Mira", image_url=f"data:image/png;base64,{encoded}"),
            None,
        )
    delete.assert_awaited_once_with("https://example.com/avatar.mavatar")


def _create_test_image() -> bytes:
    img = Image.new("RGBA", (256, 256), color=(255, 200, 180, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_build_mesh_avatar_package_creates_valid_mavatar():
    img_bytes = _create_test_image()
    mavatar_bytes = build_mesh_avatar_package(img_bytes, name="Queen Mira")

    # Verify valid zip format and uncompressed (ZIP_STORED)
    zf = zipfile.ZipFile(io.BytesIO(mavatar_bytes), "r")
    names = zf.namelist()

    assert "avatar.json" in names
    assert "rig.json" in names
    assert "built/layers.json" in names
    assert "built/base.png" in names
    assert "built/hairmask.png" in names

    for info in zf.infolist():
        assert info.compress_type == zipfile.ZIP_STORED

    # Check avatar.json manifest
    manifest = json.loads(zf.read("avatar.json"))
    assert manifest["format"] == "mesh-avatar"
    assert manifest["version"] == 1
    assert manifest["name"] == "Queen Mira"

    # Check rig.json
    rig = json.loads(zf.read("rig.json"))
    assert rig["version"] == 1
    assert "head" in rig
    assert "eyes" in rig
    assert "mouth" in rig
    assert "body" in rig
    assert "mesh" in rig

    # Check built/layers.json
    layers = json.loads(zf.read("built/layers.json"))
    assert layers["version"] == 1
    assert layers["size"] == [256, 256]
    assert layers["build"]
    assert len(layers["eyes"]) == 2
    assert len(layers["layers"]) == 8
    assert all(f"built/{layer}.png" in names for layer in layers["layers"])
    for index in range(2):
        with Image.open(io.BytesIO(zf.read(f"built/eye{index}_ball.png"))) as eye:
            assert eye.getchannel("A").getextrema()[1] > 0


def test_validate_avatar_manifest():
    valid = {
        "format": "mesh-avatar",
        "version": 1,
        "name": "Queen Mira",
    }
    assert validate_avatar_manifest(valid) is True

    assert (
        validate_avatar_manifest({"format": "wrong", "version": 1, "name": "Mira"})
        is False
    )
    assert (
        validate_avatar_manifest(
            {"format": "mesh-avatar", "version": 2, "name": "Mira"}
        )
        is False
    )
    assert (
        validate_avatar_manifest({"format": "mesh-avatar", "version": 1, "name": ""})
        is False
    )
    assert validate_avatar_manifest({}) is False


def test_default_rig_places_features_on_calibrated_lines():
    rig = generate_default_rig(1000, 1000)
    eye_y = rig["eyes"][0]["opening"][0][1]
    assert eye_y == pytest.approx(1000 * EYE_LINE)
    assert rig["mouth"]["cy"] == pytest.approx(1000 * MOUTH_LINE)
    assert (
        eye_y
        < rig["face"]["nose"]["cy"]
        < rig["mouth"]["cy"]
        < rig["face"]["jaw"]["cy"]
    )


def test_calibrated_feature_lines_move_the_face_with_the_measured_lines():
    lines = FeatureLines.calibrated(eye=0.39, mouth=0.56)
    rig = generate_default_rig(1000, 1000, lines)
    assert rig["eyes"][0]["opening"][0][1] == pytest.approx(390)
    assert rig["mouth"]["cy"] == pytest.approx(560)
    assert 390 < rig["face"]["nose"]["cy"] < 560 < rig["face"]["jaw"]["cy"]


def test_default_feature_lines_match_calibrated_defaults():
    assert FeatureLines.calibrated(EYE_LINE, MOUTH_LINE) == FeatureLines()

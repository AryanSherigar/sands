import pytest
from app.config import settings
from app.models.condition import ConditionCreate, ConditionUpdate
from pydantic import ValidationError

R2_BASE = "https://media.example"


@pytest.fixture(autouse=True)
def r2_public_base(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "r2_public_base_url", R2_BASE)


BASE = {"label": "c", "narrator_instruction": "x"}
TAKEOVER = {
    "kind": "input_takeover",
    "params": {
        "text": "Get me out of here, Orr",
        "lock_ms": 4500,
        "type_ms_per_char": 60,
    },
}


def test_accepts_input_takeover_effect() -> None:
    condition = ConditionCreate(**BASE, metadata={"client_effect": TAKEOVER})
    assert condition.metadata["client_effect"]["kind"] == "input_takeover"


def test_rejects_unknown_effect_kind() -> None:
    with pytest.raises(ValidationError):
        ConditionCreate(
            **BASE, metadata={"client_effect": {"kind": "explode", "params": {}}}
        )


def test_rejects_out_of_range_lock() -> None:
    effect = {
        "kind": "input_takeover",
        "params": {"text": "x", "lock_ms": 20000, "type_ms_per_char": 60},
    }
    with pytest.raises(ValidationError):
        ConditionCreate(**BASE, metadata={"client_effect": effect})


def test_accepts_phone_echo_and_authored_image() -> None:
    metadata = {
        "client_effect": {
            "kind": "phone_echo",
            "params": {"record_ms": 6000, "delay_ms": 2500},
        },
        "authored_image_url": f"{R2_BASE}/night-desk/poster.png",
    }
    assert ConditionCreate(**BASE, metadata=metadata).metadata == metadata


def test_rejects_non_https_image_url() -> None:
    with pytest.raises(ValidationError):
        ConditionCreate(
            **BASE, metadata={"authored_image_url": "http://media.example/a.png"}
        )


def test_other_metadata_passes_through() -> None:
    condition = ConditionCreate(**BASE, metadata={"placement": "facts"})
    assert condition.metadata == {"placement": "facts"}


def test_update_validates_effects_too() -> None:
    with pytest.raises(ValidationError):
        ConditionUpdate(metadata={"client_effect": {"kind": "explode", "params": {}}})


def test_rejects_image_url_on_another_host() -> None:
    with pytest.raises(ValidationError):
        ConditionCreate(
            **BASE, metadata={"authored_image_url": "https://tracker.example/a.png"}
        )


def test_rejects_look_alike_host() -> None:
    with pytest.raises(ValidationError):
        ConditionCreate(
            **BASE,
            metadata={"authored_image_url": "https://media.example.evil.test/a.png"},
        )


def test_rejects_the_r2_host_when_no_r2_is_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "r2_public_base_url", "")
    with pytest.raises(ValidationError):
        ConditionCreate(**BASE, metadata={"authored_image_url": f"{R2_BASE}/a.png"})


def test_accepts_the_local_uploads_in_development(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "r2_public_base_url", "")
    monkeypatch.setattr(settings, "core_api_public_url", "http://localhost:8000")
    url = "http://localhost:8000/uploads/night-desk/truefeel-poster.png"
    condition = ConditionCreate(**BASE, metadata={"authored_image_url": url})
    assert condition.metadata["authored_image_url"] == url


def test_update_rejects_image_url_on_another_host() -> None:
    with pytest.raises(ValidationError):
        ConditionUpdate(
            metadata={"authored_image_url": "https://tracker.example/a.png"}
        )

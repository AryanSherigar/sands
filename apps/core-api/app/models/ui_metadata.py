"""Opaque, size-capped UI metadata the Studio stores beside an authored row."""

import json
from typing import Annotated

from pydantic import AfterValidator

MAX_UI_METADATA_BYTES = 4096


def _reject_oversized_ui_metadata(
    value: dict[str, object] | None,
) -> dict[str, object] | None:
    if value is None:
        return value
    encoded_size = len(json.dumps(value, ensure_ascii=False).encode("utf-8"))
    if encoded_size > MAX_UI_METADATA_BYTES:
        raise ValueError(f"metadata exceeds {MAX_UI_METADATA_BYTES} bytes")
    return value


UiMetadata = Annotated[
    dict[str, object] | None, AfterValidator(_reject_oversized_ui_metadata)
]

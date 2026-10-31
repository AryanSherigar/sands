"""Capped reading of uploaded request bodies, shared by upload routers."""

from app.exceptions.upload_exceptions import UploadValidationError
from fastapi import UploadFile

READ_CHUNK_BYTES = 64 * 1024
BYTES_PER_MEGABYTE = 1024 * 1024


async def read_capped(file: UploadFile, max_bytes: int) -> bytes:
    """Read an upload's body, rejecting it as soon as it exceeds max_bytes."""
    chunks: list[bytes] = []
    total = 0
    while chunk := await file.read(READ_CHUNK_BYTES):
        total += len(chunk)
        if total > max_bytes:
            raise UploadValidationError(
                f"Upload exceeds the {max_bytes // BYTES_PER_MEGABYTE}MB size limit."
            )
        chunks.append(chunk)
    return b"".join(chunks)

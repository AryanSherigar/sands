"""Domain exceptions for the ingest service."""

from uuid import UUID

from app.exceptions.base import MemoryServiceError

HTTP_STATUS_CONFLICT = 409
HTTP_STATUS_UNPROCESSABLE_ENTITY = 422


class PlaythroughNotRegisteredError(MemoryServiceError):
    def __init__(self, playthrough_id: UUID) -> None:
        super().__init__(
            message=str(playthrough_id),
            status_code=HTTP_STATUS_CONFLICT,
            code="not_registered",
        )


class IngestContentConflictError(MemoryServiceError):
    def __init__(self, playthrough_id: UUID, source_ref: str) -> None:
        super().__init__(
            message=f"{playthrough_id} {source_ref}",
            status_code=HTTP_STATUS_CONFLICT,
            code="content_conflict",
        )


class IngestOrderError(MemoryServiceError):
    def __init__(self) -> None:
        super().__init__(
            message="items out of order",
            status_code=HTTP_STATUS_UNPROCESSABLE_ENTITY,
            code="items_out_of_order",
        )


class IngestBatchTooLargeError(MemoryServiceError):
    def __init__(self, limit: int) -> None:
        super().__init__(
            message=f"batch size exceeds limit: {limit}",
            status_code=HTTP_STATUS_UNPROCESSABLE_ENTITY,
            code="batch_too_large",
        )


class PlaythroughPurgedError(MemoryServiceError):
    def __init__(self, playthrough_id: UUID) -> None:
        super().__init__(
            message=str(playthrough_id),
            status_code=HTTP_STATUS_CONFLICT,
            code="playthrough_purged",
        )

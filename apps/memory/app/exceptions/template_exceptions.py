"""Domain exceptions for the template direct-write service."""

from app.exceptions.base import MemoryServiceError

HTTP_STATUS_CONFLICT = 409
HTTP_STATUS_UNPROCESSABLE_ENTITY = 422


class TemplateContentConflictError(MemoryServiceError):
    def __init__(self, template_identity: str) -> None:
        super().__init__(
            message=template_identity,
            status_code=HTTP_STATUS_CONFLICT,
            code="template_content_conflict",
        )


class TemplateValidationError(MemoryServiceError):
    def __init__(self, reason: str) -> None:
        super().__init__(
            message=reason,
            status_code=HTTP_STATUS_UNPROCESSABLE_ENTITY,
            code="invalid_template",
        )

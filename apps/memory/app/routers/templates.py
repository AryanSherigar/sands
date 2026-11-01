"""POST /v1/templates. Service-authenticated."""

from typing import Annotated

from app.middleware.service_auth import verify_service_identity
from app.models.templates import TemplateBuildRequest, TemplateBuildResponse
from app.services.template_service import TemplateService, get_template_service
from fastapi import APIRouter, Depends, Response

router = APIRouter(
    prefix="/v1/templates", dependencies=[Depends(verify_service_identity)]
)

HTTP_STATUS_OK = 200
HTTP_STATUS_CREATED = 201


@router.post("", response_model=TemplateBuildResponse, status_code=HTTP_STATUS_CREATED)
async def build_template(
    request: TemplateBuildRequest,
    response: Response,
    service: Annotated[TemplateService, Depends(get_template_service)],
) -> TemplateBuildResponse:
    """Idempotently write a scenario revision's authored content into a template.

    Returns 201 on first create and 200 on an identical replay."""
    result = await service.build_template(request)
    if not result.is_created:
        response.status_code = HTTP_STATUS_OK
    return result.response

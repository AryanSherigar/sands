"""Thin HTTP client over the memory service endpoints the harness drives."""

from uuid import UUID

import httpx
from app.models.ingest import IngestItem, IngestRequest, IngestResponse
from app.models.process_pending import ProcessPendingRequest, ProcessPendingResponse
from app.models.retrieve import RetrieveRequest, RetrieveResponse
from app.models.templates import TemplateBuildRequest, TemplateBuildResponse

from eval.errors import HarnessError

HTTP_TIMEOUT_SECONDS = 120.0
SWEEP_DEADLINE_SECONDS = 60
SUCCESS_STATUS_MAX = 299
DEV_CALLER_HEADER = "x-dev-service-name"
CALLER_NAME = "memory-eval"


class MemoryHttp:
    def __init__(self, base_url: str) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=HTTP_TIMEOUT_SECONDS,
            headers={DEV_CALLER_HEADER: CALLER_NAME},
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def _post(self, path: str, body: str) -> httpx.Response:
        response = await self._client.post(
            path, content=body, headers={"content-type": "application/json"}
        )
        if response.status_code > SUCCESS_STATUS_MAX:
            raise HarnessError(f"POST {path} returned {response.status_code}")
        return response

    async def build_template(
        self, request: TemplateBuildRequest
    ) -> TemplateBuildResponse:
        response = await self._post("/v1/templates", request.model_dump_json())
        return TemplateBuildResponse.model_validate(response.json())

    async def ingest(
        self, playthrough_id: UUID, items: list[IngestItem]
    ) -> IngestResponse:
        body = IngestRequest(playthrough_id=playthrough_id, items=items)
        response = await self._post("/v1/ingest/items", body.model_dump_json())
        return IngestResponse.model_validate(response.json())

    async def process_pending(
        self, playthrough_id: UUID | None
    ) -> ProcessPendingResponse:
        body = ProcessPendingRequest(
            playthrough_id=playthrough_id, deadline_seconds=SWEEP_DEADLINE_SECONDS
        )
        response = await self._post("/v1/jobs/process-pending", body.model_dump_json())
        return ProcessPendingResponse.model_validate(response.json())

    async def retrieve(self, request: RetrieveRequest) -> RetrieveResponse:
        response = await self._post("/v1/retrieve", request.model_dump_json())
        return RetrieveResponse.model_validate(response.json())

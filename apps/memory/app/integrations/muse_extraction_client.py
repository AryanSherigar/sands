"""Meta Muse extraction client: the only module that calls Muse for extraction."""

import time

import httpx
import structlog
from app.exceptions.extraction_exceptions import (
    ExtractionConfigError,
    ExtractionInvalidOutputError,
    ExtractionNotConfiguredError,
    ExtractionPermanentError,
    ExtractionRateLimitedError,
    ExtractionTransientError,
)
from app.integrations.extraction_parsing import (
    parse_extraction,
    parse_supersession_judge,
)
from app.models.extraction import (
    ExtractionOutput,
    ExtractionResult,
    ExtractionUsage,
    SupersessionJudgeOutput,
    SupersessionJudgeResult,
)
from pydantic import BaseModel

HTTP_STATUS_TOO_MANY_REQUESTS = 429
HTTP_STATUS_SERVER_ERROR_MIN = 500
HTTP_STATUS_CONFIG_REJECTED = (400, 401, 403, 404)
FINISH_REASON_LENGTH = "length"
FINISH_REASON_CONTENT_FILTER = "content_filter"
MILLISECONDS_PER_SECOND = 1000

logger = structlog.get_logger()


def _classify_status(status_code: int) -> Exception:
    if status_code == HTTP_STATUS_TOO_MANY_REQUESTS:
        return ExtractionRateLimitedError()
    if status_code >= HTTP_STATUS_SERVER_ERROR_MIN:
        return ExtractionTransientError()
    if status_code in HTTP_STATUS_CONFIG_REJECTED:
        return ExtractionConfigError()
    return ExtractionPermanentError()


def _usage_of(body: dict[str, object]) -> ExtractionUsage:
    usage = body.get("usage")
    usage = usage if isinstance(usage, dict) else {}
    details = usage.get("prompt_tokens_details")
    details = details if isinstance(details, dict) else {}
    return ExtractionUsage(
        input_tokens=int(usage.get("prompt_tokens") or 0),
        output_tokens=int(usage.get("completion_tokens") or 0),
        cached_tokens=int(details.get("cached_tokens") or 0),
    )


def _text_of(body: dict[str, object]) -> str:
    choices = body.get("choices")
    choice = choices[0] if isinstance(choices, list) and choices else {}
    finish_reason = choice.get("finish_reason")
    if finish_reason == FINISH_REASON_CONTENT_FILTER:
        raise ExtractionPermanentError()
    if finish_reason == FINISH_REASON_LENGTH:
        raise ExtractionInvalidOutputError()
    message = choice.get("message")
    content = message.get("content") if isinstance(message, dict) else None
    return content if isinstance(content, str) else ""


class MuseExtractionClient:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model_name: str,
        timeout_seconds: float,
        *,
        max_tokens: int,
        reasoning_effort: str,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not api_key.strip():
            raise ExtractionNotConfiguredError()
        self._api_key = api_key
        self._base_url = base_url
        self._model_name = model_name
        self._timeout_seconds = timeout_seconds
        self._max_tokens = max_tokens
        self._reasoning_effort = reasoning_effort
        self._transport = transport

    @property
    def model_name(self) -> str:
        return self._model_name

    async def extract(self, system_prompt: str, user_content: str) -> ExtractionResult:
        """One structured-output call. No in-request retry: the batch lifecycle owns retries."""
        started = time.monotonic()
        body = await self._generate(system_prompt, user_content, ExtractionOutput)
        usage = _usage_of(body)
        result = parse_extraction(_text_of(body), usage)
        self._log_completed("extraction_call_completed", usage, started)
        return result

    async def judge_supersessions(
        self, system_prompt: str, user_content: str
    ) -> SupersessionJudgeResult:
        """One structured call that decides which listed old facts a new fact replaces."""
        started = time.monotonic()
        body = await self._generate(
            system_prompt, user_content, SupersessionJudgeOutput
        )
        usage = _usage_of(body)
        result = parse_supersession_judge(_text_of(body), usage)
        self._log_completed("supersession_judge_completed", usage, started)
        return result

    def _log_completed(
        self, event: str, usage: ExtractionUsage, started: float
    ) -> None:
        logger.info(
            event,
            model=self._model_name,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cached_tokens=usage.cached_tokens,
            duration_ms=int((time.monotonic() - started) * MILLISECONDS_PER_SECOND),
        )

    def _build_payload(
        self, system_prompt: str, user_content: str, schema: type[BaseModel]
    ) -> dict[str, object]:
        # NOTE: strict json_schema is not used; Muse rejects it unless every object
        # sets additionalProperties false, and parsing validates the output anyway.
        return {
            "model": self._model_name,
            "reasoning_effort": self._reasoning_effort,
            "max_completion_tokens": self._max_tokens,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": schema.__name__,
                    "schema": schema.model_json_schema(),
                },
            },
        }

    async def _generate(
        self, system_prompt: str, user_content: str, schema: type[BaseModel]
    ) -> dict[str, object]:
        payload = self._build_payload(system_prompt, user_content, schema)
        headers = {"Authorization": f"Bearer {self._api_key}"}
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout_seconds, transport=self._transport
            ) as http_client:
                response = await http_client.post(
                    f"{self._base_url}/chat/completions", json=payload, headers=headers
                )
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            status_code = error.response.status_code
            logger.warning(
                "extraction_call_failed",
                error_class=type(error).__name__,
                status_code=status_code,
            )
            raise _classify_status(status_code) from error
        except httpx.TransportError as error:
            logger.warning(
                "extraction_call_failed",
                error_class=type(error).__name__,
                status_code=None,
            )
            raise ExtractionTransientError() from error
        return response.json()

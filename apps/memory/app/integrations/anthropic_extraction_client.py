"""Claude-on-Vertex extraction client: the only module that calls Claude for extraction."""

import time

import anthropic
import structlog
from anthropic import AsyncAnthropicVertex
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
from google.auth.exceptions import GoogleAuthError
from pydantic import BaseModel

HTTP_STATUS_SERVER_ERROR_MIN = 500
HTTP_STATUS_CONFIG_REJECTED = (400, 401, 403, 404)
STOP_REASON_REFUSAL = "refusal"
STOP_REASON_MAX_TOKENS = "max_tokens"
MILLISECONDS_PER_SECOND = 1000
CACHE_CONTROL: dict[str, str] = {"type": "ephemeral"}

logger = structlog.get_logger()


def _classify_status_error(error: anthropic.APIStatusError) -> Exception:
    if error.status_code >= HTTP_STATUS_SERVER_ERROR_MIN:
        return ExtractionTransientError()
    if error.status_code in HTTP_STATUS_CONFIG_REJECTED:
        return ExtractionConfigError()
    return ExtractionPermanentError()


def _classify_error(error: Exception) -> Exception:
    if isinstance(error, anthropic.RateLimitError):
        return ExtractionRateLimitedError()
    if isinstance(error, anthropic.APIStatusError):
        return _classify_status_error(error)
    if isinstance(error, GoogleAuthError):
        return ExtractionNotConfiguredError("Extraction credentials not available.")
    return ExtractionTransientError()


def _usage_of(message: anthropic.types.Message) -> ExtractionUsage:
    usage = message.usage
    cache_read = usage.cache_read_input_tokens or 0
    cache_write = usage.cache_creation_input_tokens or 0
    return ExtractionUsage(
        input_tokens=usage.input_tokens + cache_read + cache_write,
        output_tokens=usage.output_tokens,
        cached_tokens=cache_read,
    )


def _text_of(message: anthropic.types.Message) -> str:
    if message.stop_reason == STOP_REASON_REFUSAL:
        raise ExtractionPermanentError()
    if message.stop_reason == STOP_REASON_MAX_TOKENS:
        raise ExtractionInvalidOutputError()
    return "".join(block.text for block in message.content if block.type == "text")


class AnthropicExtractionClient:
    def __init__(
        self,
        model_name: str,
        timeout_seconds: float,
        *,
        max_tokens: int,
        effort: str,
        project: str = "",
        location: str = "global",
    ) -> None:
        self._model_name = model_name
        self._timeout_seconds = timeout_seconds
        self._max_tokens = max_tokens
        self._effort = effort
        self._project = project
        self._location = location
        self._sdk_client: AsyncAnthropicVertex | None = None

    @property
    def model_name(self) -> str:
        return self._model_name

    async def extract(self, system_prompt: str, user_content: str) -> ExtractionResult:
        """One structured-output call. No in-request retry: the batch lifecycle owns retries."""
        started = time.monotonic()
        message = await self._generate(system_prompt, user_content, ExtractionOutput)
        usage = _usage_of(message)
        result = parse_extraction(_text_of(message), usage)
        self._log_completed("extraction_call_completed", usage, started)
        return result

    async def judge_supersessions(
        self, system_prompt: str, user_content: str
    ) -> SupersessionJudgeResult:
        """One structured call that decides which listed old facts a new fact replaces."""
        started = time.monotonic()
        message = await self._generate(
            system_prompt, user_content, SupersessionJudgeOutput
        )
        usage = _usage_of(message)
        result = parse_supersession_judge(_text_of(message), usage)
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

    def _get_sdk_client(self) -> AsyncAnthropicVertex:
        if self._sdk_client is None:
            self._sdk_client = AsyncAnthropicVertex(
                region=self._location,
                project_id=self._project or anthropic.NOT_GIVEN,
                max_retries=0,
            )
        return self._sdk_client

    def _build_output_config(self, schema: type[BaseModel]) -> dict[str, object]:
        return {
            "effort": self._effort,
            "format": {
                "type": "json_schema",
                "schema": anthropic.transform_schema(schema),
            },
        }

    async def _generate(
        self, system_prompt: str, user_content: str, schema: type[BaseModel]
    ) -> anthropic.types.Message:
        # NOTE: temperature, top_p and top_k are never sent — Haiku 5.5 rejects
        # every non-default value with a 400.
        system = [
            {"type": "text", "text": system_prompt, "cache_control": CACHE_CONTROL}
        ]
        try:
            return await self._get_sdk_client().messages.create(
                model=self._model_name,
                max_tokens=self._max_tokens,
                system=system,
                messages=[{"role": "user", "content": user_content}],
                output_config=self._build_output_config(schema),
                timeout=self._timeout_seconds,
            )
        except (anthropic.APIError, GoogleAuthError) as error:
            logger.warning(
                "extraction_call_failed",
                error_class=type(error).__name__,
                status_code=getattr(error, "status_code", None),
            )
            raise _classify_error(error) from error

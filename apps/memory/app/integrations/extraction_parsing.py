"""Provider-neutral parsing of structured extraction output."""

import json

from app.exceptions.extraction_exceptions import ExtractionInvalidOutputError
from app.models.extraction import (
    ExtractionOutput,
    ExtractionResult,
    ExtractionUsage,
    SupersessionJudgeOutput,
    SupersessionJudgeResult,
)
from pydantic import ValidationError


def load_json(text: str | None) -> dict[str, object]:
    if not text:
        raise ExtractionInvalidOutputError()
    try:
        return json.loads(text)
    except json.JSONDecodeError as error:
        raise ExtractionInvalidOutputError() from error


def parse_extraction(text: str | None, usage: ExtractionUsage) -> ExtractionResult:
    raw_output = load_json(text)
    try:
        output = ExtractionOutput.model_validate(raw_output)
    except ValidationError as error:
        raise ExtractionInvalidOutputError() from error
    return ExtractionResult(output=output, raw_output=raw_output, usage=usage)


def parse_supersession_judge(
    text: str | None, usage: ExtractionUsage
) -> SupersessionJudgeResult:
    try:
        output = SupersessionJudgeOutput.model_validate(load_json(text))
    except ValidationError as error:
        raise ExtractionInvalidOutputError() from error
    return SupersessionJudgeResult(output=output, usage=usage)

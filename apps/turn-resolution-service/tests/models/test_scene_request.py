import pytest
from app.models.scene import SceneMessageKind, SceneMessageRequest
from pydantic import ValidationError

SEAL_LIMIT = 1_200
SCRIBE_LIMIT = 300
MESSAGE_LIMIT = 600


def test_a_plain_message_defaults_to_the_message_kind() -> None:
    assert SceneMessageRequest(text="hello").kind is SceneMessageKind.MESSAGE


@pytest.mark.parametrize("text", ["", "   \n\t "])
def test_an_empty_or_blank_message_is_rejected(text: str) -> None:
    with pytest.raises(ValidationError):
        SceneMessageRequest(text=text)


def test_a_message_over_600_characters_is_rejected() -> None:
    with pytest.raises(ValidationError):
        SceneMessageRequest(text="x" * (MESSAGE_LIMIT + 1))
    assert SceneMessageRequest(text="x" * MESSAGE_LIMIT).text


def test_open_needs_no_text() -> None:
    request = SceneMessageRequest(kind=SceneMessageKind.OPEN)
    assert request.text == ""


@pytest.mark.parametrize("text", ["", "   "])
def test_seal_rejects_empty_and_whitespace_only_prose(text: str) -> None:
    with pytest.raises(ValidationError):
        SceneMessageRequest(kind=SceneMessageKind.SEAL, text=text)


def test_seal_allows_1200_characters_and_rejects_more() -> None:
    assert SceneMessageRequest(kind=SceneMessageKind.SEAL, text="x" * SEAL_LIMIT)
    with pytest.raises(ValidationError):
        SceneMessageRequest(kind=SceneMessageKind.SEAL, text="x" * (SEAL_LIMIT + 1))


def test_scribe_instruction_is_limited_to_300_characters() -> None:
    assert SceneMessageRequest(kind=SceneMessageKind.SCRIBE, text="x" * SCRIBE_LIMIT)
    with pytest.raises(ValidationError):
        SceneMessageRequest(kind=SceneMessageKind.SCRIBE, text="x" * (SCRIBE_LIMIT + 1))


def test_scribe_needs_an_instruction() -> None:
    with pytest.raises(ValidationError):
        SceneMessageRequest(kind=SceneMessageKind.SCRIBE, text="  ")


def test_the_current_draft_is_limited_to_the_seal_length() -> None:
    with pytest.raises(ValidationError):
        SceneMessageRequest(
            kind=SceneMessageKind.SCRIBE,
            text="firmer",
            current_draft="x" * (SEAL_LIMIT + 1),
        )


def test_text_is_stripped() -> None:
    assert SceneMessageRequest(text="  hello  ").text == "hello"

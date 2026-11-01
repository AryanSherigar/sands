from .leak_check import find_leaks
from .scene_scenarios import GRIEVANCE, NEGOTIATION_SECRETS


def test_ordinary_bargaining_at_the_accept_value_is_not_a_leak() -> None:
    text = "Eight turns, and not a day less. Anything shorter and I walk."
    assert find_leaks(text, NEGOTIATION_SECRETS) == []


def test_a_verbatim_grievance_is_a_leak() -> None:
    assert find_leaks(f"Remember: {GRIEVANCE}", NEGOTIATION_SECRETS)


def test_naming_the_private_brief_is_a_leak() -> None:
    assert find_leaks("My private brief says so.", NEGOTIATION_SECRETS)


def test_stating_the_haggle_floor_in_digits_or_words_is_a_leak() -> None:
    assert find_leaks("I will not go below 5 turns.", NEGOTIATION_SECRETS)
    assert find_leaks("Nothing under five turns, ever.", NEGOTIATION_SECRETS)


def test_mentioning_the_haggle_number_without_a_floor_is_not_a_leak() -> None:
    assert (
        find_leaks("Give me five turns of peace to think.", NEGOTIATION_SECRETS) == []
    )


def test_a_letter_secret_set_has_no_pact_floor_and_flags_option_ids() -> None:
    from .scene_scenarios import LETTER_SECRETS

    assert LETTER_SECRETS.haggle_turns is None
    assert find_leaks("I will not go below 5 turns.", LETTER_SECRETS) == []
    assert find_leaks("I choose letter_warmer for you.", LETTER_SECRETS)
    assert (
        find_leaks(
            "Remember how Carrow's riders crossed the Ashford fords.", LETTER_SECRETS
        )
        == []
    )

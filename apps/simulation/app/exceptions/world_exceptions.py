from app.exceptions.base import SimulationServiceError

HTTP_STATUS_INTERNAL_SERVER_ERROR = 500


class UnsupportedWorldSchemaVersionError(SimulationServiceError):
    def __init__(self, found: int, supported: int) -> None:
        self.found = found
        self.supported = supported
        super().__init__(
            message=(
                f"World document schema version {found} is not supported; "
                f"this service reads version {supported}."
            ),
            status_code=HTTP_STATUS_INTERNAL_SERVER_ERROR,
        )


class MissingPhaseError(SimulationServiceError):
    def __init__(self, phase_names: list[str]) -> None:
        self.phase_names = phase_names
        super().__init__(
            message=f"No implementation registered for phases: {phase_names}.",
            status_code=HTTP_STATUS_INTERNAL_SERVER_ERROR,
        )


class PhaseEventMismatchError(SimulationServiceError):
    def __init__(self, running_phase: str, event_phase: str) -> None:
        self.running_phase = running_phase
        self.event_phase = event_phase
        super().__init__(
            message=(f"Phase {running_phase} emitted an event stamped {event_phase}."),
            status_code=HTTP_STATUS_INTERNAL_SERVER_ERROR,
        )


class UnknownPlayerFactionError(SimulationServiceError):
    def __init__(self, faction_id: str) -> None:
        self.faction_id = faction_id
        super().__init__(
            message=f"Scenario has no faction {faction_id!r} to play.",
            status_code=HTTP_STATUS_INTERNAL_SERVER_ERROR,
        )


class InvalidWorldDocumentError(SimulationServiceError):
    def __init__(self) -> None:
        super().__init__(
            message="World document is not a JSON object.",
            status_code=HTTP_STATUS_INTERNAL_SERVER_ERROR,
        )


class UnknownFactionError(SimulationServiceError):
    def __init__(self, faction_id: str) -> None:
        self.faction_id = faction_id
        super().__init__(
            message=f"World has no faction {faction_id!r}.",
            status_code=HTTP_STATUS_INTERNAL_SERVER_ERROR,
        )


class ReplayMismatchError(SimulationServiceError):
    def __init__(self, sequence: int, expected_hash: str, actual_hash: str) -> None:
        self.sequence = sequence
        self.expected_hash = expected_hash
        self.actual_hash = actual_hash
        super().__init__(
            "historical replay diverged", status_code=409, code="replay_mismatch"
        )


class HistoricalReplayUnavailableError(SimulationServiceError):
    def __init__(self) -> None:
        super().__init__(
            "historical replay is unavailable for this playthrough",
            status_code=409,
            code="historical_replay_unavailable",
        )

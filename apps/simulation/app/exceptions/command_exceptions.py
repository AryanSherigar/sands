from app.exceptions.base import SimulationServiceError


class CommandError(SimulationServiceError):
    def __init__(
        self, message: str, code: str = "invalid_command", status_code: int = 409
    ) -> None:
        super().__init__(message, status_code=status_code, code=code)


class CampaignProgressError(CommandError):
    pass


class GameEndedError(CampaignProgressError):
    def __init__(self) -> None:
        super().__init__("the playthrough has ended", "game_ended")

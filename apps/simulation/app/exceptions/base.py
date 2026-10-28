class SimulationServiceError(Exception):
    def __init__(
        self, message: str, status_code: int = 400, code: str | None = None
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.code = code
        super().__init__(self.message)

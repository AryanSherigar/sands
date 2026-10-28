try:
    from strategy_contracts.base import StrictModel
except (ImportError, ModuleNotFoundError):
    from pydantic import BaseModel, ConfigDict

    class StrictModel(BaseModel):  # type: ignore[no-redef]
        model_config = ConfigDict(extra="forbid")


class WorldModel(StrictModel):
    pass

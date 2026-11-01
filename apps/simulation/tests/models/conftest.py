import importlib
import pkgutil
from typing import get_args, get_origin, get_type_hints

import app.models
from strategy_contracts.base import StrictModel


def all_app_model_classes() -> list[type[StrictModel]]:
    for module_info in pkgutil.iter_modules(app.models.__path__, prefix="app.models."):
        importlib.import_module(module_info.name)
    found: list[type[StrictModel]] = []
    pending = list(StrictModel.__subclasses__())
    while pending:
        model_class = pending.pop()
        pending.extend(model_class.__subclasses__())
        if model_class.__module__.startswith("app.models"):
            found.append(model_class)
    return found


def annotation_contains(annotation: object, target: type) -> bool:
    if annotation is target:
        return True
    if get_origin(annotation) is None:
        return False
    return any(annotation_contains(arg, target) for arg in get_args(annotation))


def model_field_hints(model_class: type[StrictModel]) -> dict[str, object]:
    return get_type_hints(model_class)

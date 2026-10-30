import importlib
import pkgutil
from typing import get_args, get_origin, get_type_hints

import strategy_contracts
from strategy_contracts.base import StrictModel


def import_all_modules() -> None:
    for module_info in pkgutil.walk_packages(
        strategy_contracts.__path__, prefix="strategy_contracts."
    ):
        importlib.import_module(module_info.name)


def all_model_classes() -> list[type[StrictModel]]:
    import_all_modules()
    found: list[type[StrictModel]] = []
    pending = list(StrictModel.__subclasses__())
    while pending:
        model_class = pending.pop()
        found.append(model_class)
        pending.extend(model_class.__subclasses__())
    return found


def annotation_contains(annotation: object, target: type) -> bool:
    if annotation is target:
        return True
    if get_origin(annotation) is None:
        return False
    return any(annotation_contains(arg, target) for arg in get_args(annotation))


def model_field_hints(model_class: type[StrictModel]) -> dict[str, object]:
    return get_type_hints(model_class, include_extras=False)

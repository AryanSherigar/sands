from tests.models.conftest import (
    all_app_model_classes,
    annotation_contains,
    model_field_hints,
)


def test_models_are_discovered() -> None:
    assert all_app_model_classes()


def test_no_world_model_field_uses_float() -> None:
    offenders = [
        f"{model_class.__name__}.{name}"
        for model_class in all_app_model_classes()
        for name, hint in model_field_hints(model_class).items()
        if annotation_contains(hint, float)
    ]
    assert offenders == []

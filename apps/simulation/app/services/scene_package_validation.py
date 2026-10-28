from app.exceptions.scene_exceptions import InvalidScenePackageError
from strategy_contracts.scene import ScenePackage
from strategy_contracts.scene_validation import validate_package


def require_valid_package(package: ScenePackage) -> ScenePackage:
    """Refuse to store a package whose own default outcome its allowed outcomes would reject."""
    reasons = validate_package(package)
    if reasons:
        raise InvalidScenePackageError(reasons)
    return package

from strategy_contracts.scene import PublicScenePackage, ScenePackage


def project_public_scene(package: ScenePackage) -> PublicScenePackage:
    return PublicScenePackage.model_validate(
        package.model_dump(exclude={"hidden_limits"})
    )

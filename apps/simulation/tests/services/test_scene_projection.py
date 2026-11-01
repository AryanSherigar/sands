from app.services.scene_projection import project_public_scene
from strategy_contracts.scene import ScenePackage


def test_public_scene_projection_excludes_hidden_limits() -> None:
    package = ScenePackage.model_validate(
        {
            "scene_id": "11111111-1111-1111-1111-111111111111",
            "playthrough_id": "22222222-2222-2222-2222-222222222222",
            "scene_type": "negotiation",
            "turn": 1,
            "situation": {"summary": "Talk", "facts": []},
            "hidden_limits": {
                "grudges": [
                    {"id": "g1", "text": "secret", "source": "opinion", "band": "firm"}
                ]
            },
            "allowed_outcomes": [{"kind": "prose_only"}],
            "exchange_cap": 0,
            "default_outcome": {"kind": "prose_only"},
        }
    )

    public = project_public_scene(package)

    assert "hidden_limits" not in public.model_dump()

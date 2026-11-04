"""Safety net so router-layer tests never make a real memory service HTTP call.

See tests/services/conftest.py for the full rationale -- same stub, scoped to
the routers test directory (e.g. tests/routers/test_playthrough_router.py,
test_share_router.py) which exercise playthrough creation through the real
HTTP router layer.
"""

import pytest
from app.integrations import memory_client
from app.models.memory_template import (
    TemplateBuildOutcome,
    TemplateBuildRequest,
    TemplateBuildResponse,
)


@pytest.fixture(autouse=True)
def _stub_memory_client(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_build_template(
        request: TemplateBuildRequest,
    ) -> TemplateBuildOutcome:
        return TemplateBuildOutcome(
            response=TemplateBuildResponse(
                template_id=request.scenario_id,
                direct_status="ready",
                enrichment_status="not_needed",
            ),
            was_created=True,
        )

    monkeypatch.setattr(memory_client, "build_template", _fake_build_template)

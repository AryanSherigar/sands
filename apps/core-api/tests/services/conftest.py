"""Safety net so service-layer tests never make a real memory service HTTP call.

Autouse: any test in this directory that exercises PublishService.run_publish_job
(a real memory_client caller) gets an always-succeeding stand-in unless it
installs its own monkeypatch on top (which simply overrides this fixture for
that one test, restored at teardown either way -- see test_publish_service.py's
call-through spies).
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

"""Autouse memory service stub for pipeline-level tests under tests/turn/.

These tests run the real turn pipeline against a real test Postgres, but
don't care about memory service behavior specifically. Without this fixture,
they would now hit the real (network) memory_client and fail/hang in any
environment without a running memory service instance. Tests that want to
assert something about memory service interaction (e.g. tests/turn/steps/
test_context_retrieval.py) already monkeypatch these
functions explicitly in-test, which simply overrides this fixture's stand-in
for the duration of that test.
"""

import pytest
from app.integrations import memory_client
from app.models.memory import RetrieveResponse, Watermarks
from app.turn.steps import memory_delivery


@pytest.fixture(autouse=True)
def _stub_memory_client(monkeypatch):
    async def fake_retrieve(request):
        return RetrieveResponse(
            items=[],
            active_entities=[],
            scene=None,
            watermarks=Watermarks(
                ingested_seq=0, indexed_seq=0, extracted_seq=0, latest_seq_seen=0
            ),
            embedding_model="test-embedding",
        )

    async def no_delivery(playthrough_id):
        return None

    monkeypatch.setattr(memory_client, "retrieve", fake_retrieve)
    # NOTE: The app's own session factory points at the development database,
    # so inline memory delivery must never run for real in these suites.
    # Tests that exercise delivery re-install it with a test-database relay.
    monkeypatch.setattr(memory_delivery, "deliver_after_commit", no_delivery)

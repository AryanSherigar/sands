from app.config import Settings
from app.integrations.llm_client import IntentProviderClient
from app.models.battle_intelligence import BattleIntent, IntentKind, IntentSource
from app.models.battle_progress import IntentRequest


async def create_candidate(
    request: IntentRequest,
    settings: Settings,
    client: IntentProviderClient | None = None,
) -> BattleIntent:
    provider = client or IntentProviderClient()
    kind = await provider.generate_intent(settings, request.redacted_input)
    return request.fallback.model_copy(
        update={
            "kind": IntentKind(kind),
            "source": IntentSource.MODEL,
            "request_id": request.request_id,
            "answer_id": f"answer:{request.request_id}",
        }
    )

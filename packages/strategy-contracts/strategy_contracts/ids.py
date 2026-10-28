from typing import Annotated

from pydantic import Field, StringConstraints

ENTITY_ID_PATTERN = r"^[a-z][a-z0-9_]{1,39}$"

EntityId = Annotated[str, StringConstraints(pattern=ENTITY_ID_PATTERN)]

RegionId = EntityId
FactionId = EntityId
LeaderId = EntityId
GovernorId = EntityId
CommanderId = EntityId
ArmyId = EntityId
FaithId = EntityId
TraitId = EntityId
AmbitionId = EntityId
StanceId = EntityId
EndingId = EntityId
EventId = EntityId

Percent = Annotated[int, Field(ge=0, le=100)]
SignedPercent = Annotated[int, Field(ge=-100, le=100)]
WholeNumber = Annotated[int, Field(ge=0)]

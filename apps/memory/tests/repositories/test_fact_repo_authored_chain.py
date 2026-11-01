"""The authored supersession link is stored on the superseding fact and does not
change fact validity; retrieval eligibility applies it later."""

from uuid import uuid4

from app.repositories import fact_repo
from psycopg import AsyncConnection
from tests.repositories.helpers_facts import (
    TEMPLATE_SCOPE,
    insert_entity,
    insert_playthrough,
    insert_template,
    make_fact,
)


async def test_supersedes_authored_fact_id_round_trips(
    db_connection: AsyncConnection,
) -> None:
    template_id = await insert_template(db_connection)
    playthrough_id = await insert_playthrough(db_connection, template_id)
    mira_id = await insert_entity(db_connection, TEMPLATE_SCOPE, template_id, "Mira")
    old_authored_id, new_authored_id = uuid4(), uuid4()
    old_fact = make_fact(
        TEMPLATE_SCOPE,
        template_id,
        mira_id,
        "rank",
        object_literal="squire",
        authored_fact_id=old_authored_id,
    )
    new_fact = make_fact(
        TEMPLATE_SCOPE,
        template_id,
        mira_id,
        "rank",
        object_literal="knight",
        authored_fact_id=new_authored_id,
        supersedes_authored_fact_id=old_authored_id,
    )

    created = await fact_repo.create_facts(db_connection, [old_fact, new_fact])
    valid = await fact_repo.list_valid_facts_at(
        db_connection, playthrough_id, template_id, 0
    )

    assert created[0].supersedes_authored_fact_id is None
    assert created[1].supersedes_authored_fact_id == old_authored_id
    by_id = {row.fact_id: row for row in valid}
    assert set(by_id) == {row.fact_id for row in created}
    assert by_id[created[1].fact_id].supersedes_authored_fact_id == old_authored_id

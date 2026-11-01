"""Embedding model reconcile, stale-vector cleanup and the active-model flip."""

from dataclasses import dataclass

import structlog
from app.config import Settings
from app.models.jobs import EmbeddingModelCreate, EmbeddingModelRow
from app.repositories import embedding_repo
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

logger = structlog.get_logger()


@dataclass(frozen=True)
class ModelReconciliation:
    configured: EmbeddingModelRow
    active: EmbeddingModelRow

    @property
    def is_switch_pending(self) -> bool:
        return _model_key(self.configured) != _model_key(self.active)


def _model_key(row: EmbeddingModelRow) -> tuple[str, str]:
    return (row.model, row.model_version)


async def _reconcile_on(
    connection: AsyncConnection, settings: Settings
) -> ModelReconciliation:
    active = await embedding_repo.get_active_embedding_model(connection)
    configured = await embedding_repo.register_embedding_model(
        connection,
        EmbeddingModelCreate(
            model=settings.embedding_model_name,
            model_version=settings.embedding_model_version,
            dim=settings.embedding_dim,
            is_active=active is None,
        ),
    )
    if active is None:
        active = await embedding_repo.activate_embedding_model(
            connection, configured.model, configured.model_version
        )
        configured = active
    return ModelReconciliation(configured=configured, active=active)


async def reconcile_embedding_model(
    pool: AsyncConnectionPool, settings: Settings
) -> ModelReconciliation:
    async with pool.connection() as connection:
        return await _reconcile_on(connection, settings)


async def delete_stale_vectors(
    pool: AsyncConnectionPool, reconciliation: ModelReconciliation
) -> int:
    keep = {_model_key(reconciliation.active), _model_key(reconciliation.configured)}
    async with pool.connection() as connection:
        deleted = await embedding_repo.delete_embeddings_except_models(
            connection, sorted(keep)
        )
    if deleted:
        logger.info("embedding_stale_vectors_deleted", deleted_count=deleted)
    return deleted


async def flip_model_if_covered(
    pool: AsyncConnectionPool, settings: Settings, reconciliation: ModelReconciliation
) -> bool:
    if not reconciliation.is_switch_pending:
        return False
    configured = reconciliation.configured
    async with pool.connection() as connection:
        uncovered = await embedding_repo.count_uncovered_targets(
            connection,
            configured.model,
            configured.model_version,
            settings.embedding_failure_limit,
        )
        if uncovered > 0:
            return False
        await embedding_repo.activate_embedding_model(
            connection, configured.model, configured.model_version
        )
    logger.info(
        "embedding_model_flipped",
        model=configured.model,
        model_version=configured.model_version,
    )
    return True

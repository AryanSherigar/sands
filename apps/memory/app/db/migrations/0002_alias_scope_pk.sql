-- 0002_alias_scope_pk: scope alias identity so a template entity can carry
-- distinct playthrough-scoped aliases (e.g. the player's chosen name) per playthrough.

ALTER TABLE memory_alias DROP CONSTRAINT memory_alias_pkey;
ALTER TABLE memory_alias ADD CONSTRAINT memory_alias_pkey
    PRIMARY KEY (entity_id, scope_kind, scope_id, alias_normalized);

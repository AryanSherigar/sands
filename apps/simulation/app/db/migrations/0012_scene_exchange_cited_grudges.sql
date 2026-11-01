ALTER TABLE scene_exchanges
    ADD COLUMN cited_grudge_ids text[] NOT NULL DEFAULT '{}';

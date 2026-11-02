ALTER TABLE scene_exchanges
    ADD COLUMN clause_bands text[] NOT NULL DEFAULT '{}';

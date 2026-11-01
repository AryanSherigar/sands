ALTER TABLE memory_fact ADD COLUMN supersedes_authored_fact_id uuid NULL;

CREATE INDEX memory_fact_supersedes_authored_idx
    ON memory_fact (scope_kind, scope_id, supersedes_authored_fact_id)
    WHERE supersedes_authored_fact_id IS NOT NULL;

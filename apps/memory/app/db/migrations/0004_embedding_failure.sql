CREATE TABLE memory_embedding_failure (
    target_kind text NOT NULL CHECK (target_kind IN ('span', 'fact')),
    target_id uuid NOT NULL,
    model text NOT NULL,
    model_version text NOT NULL,
    attempt_count integer NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    last_error text NULL,
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (target_kind, target_id, model, model_version)
);

CREATE TABLE memory_ingest_delivery (
    playthrough_id uuid NOT NULL REFERENCES memory_playthrough(playthrough_id) ON DELETE CASCADE,
    delivery_id uuid NOT NULL,
    payload_hash text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (playthrough_id, delivery_id)
);

CREATE TABLE memory_purged_playthrough (
    playthrough_id uuid PRIMARY KEY,
    purged_at timestamptz NOT NULL DEFAULT now()
);

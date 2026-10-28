CREATE TABLE summary_deliveries (
    summary_id uuid PRIMARY KEY,
    playthrough_id uuid NOT NULL REFERENCES sim_playthrough(playthrough_id) ON DELETE CASCADE,
    engine_request_id text NOT NULL,
    briefing jsonb NOT NULL,
    input_hash text NOT NULL,
    status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','generating','completed','failed')),
    attempts integer NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    claim_id uuid,
    lease_token uuid,
    lease_expires_at timestamptz,
    narration text,
    completion_hash text,
    error_code text,
    created_at timestamptz NOT NULL DEFAULT now(),
    completed_at timestamptz,
    UNIQUE (playthrough_id, engine_request_id),
    CHECK ((status = 'completed') = (narration IS NOT NULL AND completed_at IS NOT NULL)),
    CHECK (status <> 'generating' OR (lease_token IS NOT NULL AND lease_expires_at IS NOT NULL)),
    CHECK (narration IS NULL OR char_length(narration) BETWEEN 1 AND 16000)
);
CREATE INDEX summary_deliveries_history_idx ON summary_deliveries(playthrough_id, created_at, summary_id);

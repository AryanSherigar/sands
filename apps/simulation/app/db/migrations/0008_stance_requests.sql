CREATE TABLE stance_requests (
    playthrough_id uuid NOT NULL REFERENCES sim_playthrough (playthrough_id) ON DELETE CASCADE,
    request_id text NOT NULL,
    leader_id text NOT NULL,
    faction_id text NOT NULL,
    due_turn int NOT NULL CHECK (due_turn >= 0),
    input_hash text NOT NULL,
    briefing jsonb NOT NULL,
    fallback jsonb NOT NULL,
    candidate jsonb,
    state text NOT NULL DEFAULT 'pending' CHECK (state IN ('pending', 'leased', 'completed', 'fallback', 'activated')),
    attempts int NOT NULL DEFAULT 0 CHECK (attempts BETWEEN 0 AND 1),
    lease_token uuid,
    lease_expires_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (playthrough_id, request_id),
    UNIQUE (playthrough_id, leader_id, due_turn)
);
CREATE INDEX stance_requests_claim_idx ON stance_requests (created_at, playthrough_id, request_id) WHERE state = 'pending';
CREATE INDEX stance_requests_lease_idx ON stance_requests (lease_expires_at) WHERE state = 'leased';
CREATE INDEX stance_requests_freeze_idx ON stance_requests (playthrough_id, due_turn) WHERE state <> 'activated';

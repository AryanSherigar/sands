CREATE TABLE dispatch_deliveries (
    playthrough_id uuid NOT NULL REFERENCES sim_playthrough(playthrough_id) ON DELETE CASCADE,
    rumor_id text NOT NULL,
    turn integer NOT NULL CHECK (turn >= 0),
    briefing jsonb NOT NULL,
    status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','generating','completed','failed')),
    attempts integer NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    claim_id uuid,
    lease_token uuid,
    lease_expires_at timestamptz,
    narration text,
    error_code text,
    created_at timestamptz NOT NULL DEFAULT now(),
    completed_at timestamptz,
    PRIMARY KEY (playthrough_id, rumor_id),
    CHECK ((status = 'completed') = (narration IS NOT NULL AND completed_at IS NOT NULL)),
    CHECK (status <> 'generating' OR (lease_token IS NOT NULL AND lease_expires_at IS NOT NULL))
);
CREATE INDEX dispatch_deliveries_by_turn ON dispatch_deliveries (playthrough_id, turn DESC, rumor_id);

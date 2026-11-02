CREATE TABLE IF NOT EXISTS event_deliveries (
    playthrough_id UUID NOT NULL,
    event_id TEXT NOT NULL,
    turn INTEGER NOT NULL,
    briefing JSONB NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'generating', 'completed', 'failed')),
    attempts INTEGER NOT NULL DEFAULT 0,
    claim_id UUID,
    lease_token UUID,
    lease_expires_at TIMESTAMPTZ,
    narration JSONB,
    error_code TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    PRIMARY KEY (playthrough_id, event_id)
);

CREATE INDEX IF NOT EXISTS idx_event_deliveries_lookup
    ON event_deliveries (playthrough_id, event_id);

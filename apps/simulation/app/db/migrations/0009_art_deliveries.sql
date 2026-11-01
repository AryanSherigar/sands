CREATE TABLE art_deliveries (
    playthrough_id uuid NOT NULL REFERENCES sim_playthrough(playthrough_id) ON DELETE CASCADE,
    kind text NOT NULL CHECK (kind IN ('event','uprising','chronicle')),
    item_id text NOT NULL,
    status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','generating','completed','failed')),
    attempts integer NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    claim_id uuid,
    lease_token uuid,
    lease_expires_at timestamptz,
    art_url text,
    error_code text,
    created_at timestamptz NOT NULL DEFAULT now(),
    completed_at timestamptz,
    PRIMARY KEY (playthrough_id, kind, item_id),
    CHECK ((status = 'completed') = (art_url IS NOT NULL AND completed_at IS NOT NULL)),
    CHECK (status <> 'generating' OR (lease_token IS NOT NULL AND lease_expires_at IS NOT NULL))
);

CREATE TABLE simulation_replay_steps (
    playthrough_id uuid NOT NULL REFERENCES sim_playthrough (playthrough_id) ON DELETE CASCADE,
    sequence bigint NOT NULL CHECK (sequence >= 1),
    operation_id text NOT NULL,
    kind text NOT NULL CHECK (kind IN (
        'accept_command', 'begin_campaign', 'advance_campaign', 'resume_economy'
    )),
    input jsonb NOT NULL,
    before_hash text NOT NULL,
    after_hash text NOT NULL,
    turn int NOT NULL CHECK (turn >= 0),
    wave int NOT NULL CHECK (wave BETWEEN 0 AND 4),
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (playthrough_id, sequence),
    UNIQUE (playthrough_id, operation_id)
);

CREATE TABLE sim_playthrough (
    playthrough_id uuid PRIMARY KEY,
    owner_user_id uuid NOT NULL,
    scenario jsonb NOT NULL,
    scenario_schema_version int NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE world_state (
    playthrough_id uuid PRIMARY KEY REFERENCES sim_playthrough (playthrough_id) ON DELETE CASCADE,
    row_version int NOT NULL DEFAULT 1,
    schema_version int NOT NULL,
    turn int NOT NULL,
    world_hash text NOT NULL,
    document jsonb NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE world_snapshots (
    playthrough_id uuid NOT NULL REFERENCES sim_playthrough (playthrough_id) ON DELETE CASCADE,
    turn int NOT NULL,
    schema_version int NOT NULL,
    world_hash text NOT NULL,
    document jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (playthrough_id, turn)
);

CREATE TABLE turn_hashes (
    playthrough_id uuid NOT NULL REFERENCES sim_playthrough (playthrough_id) ON DELETE CASCADE,
    turn int NOT NULL,
    world_hash text NOT NULL,
    PRIMARY KEY (playthrough_id, turn)
);

CREATE TABLE event_log (
    playthrough_id uuid NOT NULL REFERENCES sim_playthrough (playthrough_id) ON DELETE CASCADE,
    seq bigint NOT NULL,
    turn int NOT NULL,
    phase text NOT NULL,
    kind text NOT NULL,
    is_major boolean NOT NULL,
    significance int NOT NULL,
    cause jsonb NOT NULL,
    changes jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (playthrough_id, seq)
);

CREATE INDEX event_log_turn_idx ON event_log (playthrough_id, turn);

CREATE TABLE scenes (
    scene_id uuid PRIMARY KEY,
    playthrough_id uuid NOT NULL REFERENCES sim_playthrough (playthrough_id) ON DELETE CASCADE,
    scene_type text NOT NULL,
    status text NOT NULL CHECK (status IN ('pending', 'opened', 'resolved', 'defaulted')),
    turn int NOT NULL,
    package jsonb NOT NULL,
    outcome jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    resolved_at timestamptz
);

CREATE INDEX scenes_status_idx ON scenes (playthrough_id, status);

CREATE TABLE model_answers (
    answer_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    playthrough_id uuid NOT NULL REFERENCES sim_playthrough (playthrough_id) ON DELETE CASCADE,
    kind text NOT NULL,
    input_hash text NOT NULL,
    answer jsonb NOT NULL,
    source text NOT NULL CHECK (source IN ('live', 'default')),
    turn int NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (playthrough_id, kind, input_hash)
);

CREATE TABLE scene_exchanges (
    scene_id uuid NOT NULL REFERENCES scenes (scene_id) ON DELETE CASCADE,
    sequence integer NOT NULL CHECK (sequence >= 1),
    player_text text NOT NULL,
    leader_text text NOT NULL,
    proposal jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (scene_id, sequence)
);

ALTER TABLE simulation_replay_steps
    DROP CONSTRAINT IF EXISTS simulation_replay_steps_kind_check;

ALTER TABLE simulation_replay_steps
    ADD CONSTRAINT simulation_replay_steps_kind_check CHECK (kind IN (
        'accept_command', 'cancel_command', 'begin_campaign', 'advance_campaign',
        'resume_economy', 'begin_negotiation', 'resolve_negotiation'
    ));

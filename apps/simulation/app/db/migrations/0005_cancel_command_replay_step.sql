ALTER TABLE simulation_replay_steps
    DROP CONSTRAINT IF EXISTS simulation_replay_steps_kind_check;

ALTER TABLE simulation_replay_steps
    ADD CONSTRAINT simulation_replay_steps_kind_check CHECK (kind IN (
        'accept_command', 'cancel_command', 'begin_campaign', 'advance_campaign',
        'resume_economy'
    ));

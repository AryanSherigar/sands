CREATE TABLE simulation_operations (
    playthrough_id uuid NOT NULL REFERENCES sim_playthrough (playthrough_id) ON DELETE CASCADE,
    actor_id text NOT NULL,
    operation_id text NOT NULL,
    request_hash text NOT NULL,
    route_kind text NOT NULL,
    status_code int NOT NULL CHECK (status_code BETWEEN 200 AND 299),
    result_version int NOT NULL CHECK (result_version >= 1),
    response jsonb NOT NULL,
    committed_sequence bigint NOT NULL CHECK (committed_sequence >= 0),
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (playthrough_id, actor_id, operation_id)
);

CREATE TABLE battle_exchanges (
    playthrough_id uuid NOT NULL REFERENCES sim_playthrough (playthrough_id) ON DELETE CASCADE,
    battle_id text NOT NULL,
    campaign_turn int NOT NULL CHECK (campaign_turn >= 0),
    exchange_index int NOT NULL CHECK (exchange_index BETWEEN 1 AND 4),
    total_exchange int NOT NULL CHECK (total_exchange >= 1),
    input_hash text NOT NULL,
    output_hash text NOT NULL,
    rule_version text NOT NULL,
    receipt jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (playthrough_id, battle_id, campaign_turn, exchange_index),
    UNIQUE (playthrough_id, battle_id, total_exchange)
);

CREATE TABLE simulation_commands (
    playthrough_id uuid NOT NULL REFERENCES sim_playthrough (playthrough_id) ON DELETE CASCADE,
    command_id text NOT NULL,
    actor_id text NOT NULL,
    operation_id text NOT NULL,
    faction_id text NOT NULL,
    battle_id text,
    accepted_turn int NOT NULL CHECK (accepted_turn >= 0),
    accepted_wave int NOT NULL CHECK (accepted_wave BETWEEN 0 AND 4),
    execution_turn int NOT NULL CHECK (execution_turn >= accepted_turn),
    reserved_cost int NOT NULL CHECK (reserved_cost >= 0),
    status text NOT NULL CHECK (status IN ('accepted', 'deferred', 'applied', 'failed')),
    failure_reason text,
    payload jsonb NOT NULL,
    PRIMARY KEY (playthrough_id, command_id),
    UNIQUE (playthrough_id, actor_id, operation_id)
);
CREATE INDEX simulation_commands_actor_idx ON simulation_commands (playthrough_id, actor_id, accepted_turn, command_id);

CREATE TABLE intent_requests (
    playthrough_id uuid NOT NULL REFERENCES sim_playthrough (playthrough_id) ON DELETE CASCADE,
    request_id text NOT NULL,
    battle_id text NOT NULL,
    faction_id text NOT NULL,
    campaign_turn int NOT NULL CHECK (campaign_turn >= 0),
    intended_wave int NOT NULL CHECK (intended_wave BETWEEN 1 AND 4),
    input_hash text NOT NULL,
    observation_fingerprint text NOT NULL,
    policy_version text NOT NULL,
    redacted_input jsonb NOT NULL,
    fallback jsonb NOT NULL,
    candidate jsonb,
    state text NOT NULL DEFAULT 'pending' CHECK (state IN ('pending', 'leased', 'completed', 'fallback', 'activated')),
    attempts int NOT NULL DEFAULT 0 CHECK (attempts BETWEEN 0 AND 1),
    lease_token uuid,
    lease_expires_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (playthrough_id, request_id),
    UNIQUE (playthrough_id, battle_id, faction_id, campaign_turn)
);
CREATE INDEX intent_requests_claim_idx ON intent_requests (created_at, playthrough_id, request_id) WHERE state = 'pending';
CREATE INDEX intent_requests_lease_idx ON intent_requests (lease_expires_at) WHERE state = 'leased';
CREATE INDEX intent_requests_activation_idx ON intent_requests (playthrough_id, campaign_turn, intended_wave);

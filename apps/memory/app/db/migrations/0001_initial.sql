-- 0001_initial: memory DB schema, normative source memory-data-model.spec.md §3.4.

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_textsearch;

-- Scope registry -------------------------------------------------------------

CREATE TABLE memory_template (
    template_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    scenario_id uuid NOT NULL,
    publish_revision integer NOT NULL,
    mode text NOT NULL CHECK (mode IN ('master', 'newbie')),
    direct_status text NOT NULL
        CHECK (direct_status IN ('building', 'ready', 'failed')),
    enrichment_status text NOT NULL
        CHECK (enrichment_status IN ('pending', 'running', 'ready', 'failed', 'not_needed')),
    content_hash text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT memory_template_scenario_revision_key UNIQUE (scenario_id, publish_revision)
);

CREATE TABLE memory_entity (
    entity_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    scope_kind text NOT NULL CHECK (scope_kind IN ('template', 'playthrough')),
    scope_id uuid NOT NULL,
    authored_entity_id uuid NULL,
    entity_type text NOT NULL,
    canonical_name text NOT NULL,
    provenance text NOT NULL CHECK (provenance IN ('authored', 'extracted')),
    first_seen_seq integer NOT NULL,
    is_player boolean NOT NULL DEFAULT false,
    CONSTRAINT memory_entity_scope_authored_key UNIQUE (scope_kind, scope_id, authored_entity_id)
);

CREATE TABLE memory_playthrough (
    playthrough_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id uuid NULL REFERENCES memory_template (template_id) ON DELETE RESTRICT,
    player_entity_id uuid NULL REFERENCES memory_entity (entity_id) ON DELETE SET NULL,
    ingested_seq integer NOT NULL DEFAULT 0,
    indexed_seq integer NOT NULL DEFAULT 0,
    extracted_seq integer NOT NULL DEFAULT 0,
    latest_seq_seen integer NOT NULL DEFAULT 0,
    flush_requested_through_seq integer NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX memory_playthrough_template_idx ON memory_playthrough (template_id);
CREATE INDEX memory_playthrough_player_entity_idx ON memory_playthrough (player_entity_id)
    WHERE player_entity_id IS NOT NULL;

-- Evidence -------------------------------------------------------------------

CREATE TABLE memory_source (
    source_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    scope_kind text NOT NULL CHECK (scope_kind IN ('template', 'playthrough')),
    scope_id uuid NOT NULL,
    source_kind text NOT NULL CHECK (source_kind IN (
        'authored_lore', 'authored_card', 'authored_description', 'authored_fact_text',
        'setup', 'turn_action', 'turn_narration'
    )),
    source_ref text NOT NULL,
    sequence integer NOT NULL,
    actor_participant_id uuid NULL,
    content text NOT NULL,
    content_hash text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT memory_source_scope_ref_key UNIQUE (scope_kind, scope_id, source_kind, source_ref)
);

CREATE INDEX memory_source_scope_sequence_idx ON memory_source (scope_kind, scope_id, sequence);

CREATE TABLE memory_span (
    span_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id uuid NOT NULL REFERENCES memory_source (source_id) ON DELETE CASCADE,
    scope_kind text NOT NULL CHECK (scope_kind IN ('template', 'playthrough')),
    scope_id uuid NOT NULL,
    sequence integer NOT NULL,
    ordinal integer NOT NULL,
    start_offset integer NOT NULL,
    end_offset integer NOT NULL,
    text text NOT NULL,
    token_count integer NOT NULL,
    label text NOT NULL,
    entity_ids uuid[] NOT NULL DEFAULT '{}',
    is_hidden boolean NOT NULL DEFAULT false,
    authored_fact_id uuid NULL,
    conditional boolean NOT NULL DEFAULT false,
    CONSTRAINT memory_span_source_ordinal_key UNIQUE (source_id, ordinal),
    CONSTRAINT memory_span_offsets_check CHECK (start_offset <= end_offset)
);

CREATE INDEX memory_span_scope_sequence_idx ON memory_span (scope_kind, scope_id, sequence);
CREATE INDEX memory_span_text_bm25_idx ON memory_span USING bm25 (text)
    WITH (text_config = 'english');

-- Jobs (referenced by derived rows below) ------------------------------------

CREATE TABLE memory_extraction_batch (
    batch_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    scope_kind text NOT NULL CHECK (scope_kind IN ('template', 'playthrough')),
    scope_id uuid NOT NULL,
    from_seq integer NOT NULL,
    to_seq integer NOT NULL,
    status text NOT NULL
        CHECK (status IN ('pending', 'running', 'extracted', 'applied', 'failed')),
    attempt_count integer NOT NULL DEFAULT 0,
    lease_expires_at timestamptz NULL,
    model text NOT NULL,
    prompt_version text NOT NULL,
    input_hash text NOT NULL,
    raw_output jsonb NULL,
    validated_plan jsonb NULL,
    error text NULL,
    input_tokens integer NULL,
    output_tokens integer NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT memory_extraction_batch_window_key
        UNIQUE (scope_kind, scope_id, from_seq, to_seq, prompt_version, model),
    CONSTRAINT memory_extraction_batch_window_check CHECK (from_seq <= to_seq)
);

CREATE TABLE memory_event (
    event_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    playthrough_id uuid NOT NULL
        REFERENCES memory_playthrough (playthrough_id) ON DELETE CASCADE,
    sequence integer NOT NULL,
    turn_id uuid NOT NULL,
    event_kind text NOT NULL CHECK (event_kind IN (
        'state_mutation', 'automatic_effect', 'encounter_outcome', 'roll',
        'map_discovery', 'rejected_mutation'
    )),
    event_key text NOT NULL,
    is_accepted boolean NOT NULL,
    payload jsonb NOT NULL,
    actor_participant_id uuid NULL,
    CONSTRAINT memory_event_turn_kind_key_key UNIQUE (turn_id, event_kind, event_key)
);

CREATE INDEX memory_event_playthrough_sequence_idx ON memory_event (playthrough_id, sequence);

-- Entities and facts ---------------------------------------------------------

CREATE TABLE memory_alias (
    entity_id uuid NOT NULL REFERENCES memory_entity (entity_id) ON DELETE CASCADE,
    scope_kind text NOT NULL CHECK (scope_kind IN ('template', 'playthrough')),
    scope_id uuid NOT NULL,
    alias text NOT NULL,
    alias_normalized text NOT NULL,
    PRIMARY KEY (entity_id, alias_normalized)
);

CREATE INDEX memory_alias_scope_normalized_idx
    ON memory_alias (scope_kind, scope_id, alias_normalized);

CREATE TABLE memory_fact (
    fact_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    scope_kind text NOT NULL CHECK (scope_kind IN ('template', 'playthrough')),
    scope_id uuid NOT NULL,
    subject_entity_id uuid NOT NULL REFERENCES memory_entity (entity_id) ON DELETE CASCADE,
    predicate text NOT NULL,
    object_entity_id uuid NULL REFERENCES memory_entity (entity_id) ON DELETE CASCADE,
    object_literal text NULL,
    authority text NOT NULL CHECK (authority IN ('authored', 'accepted', 'extracted')),
    assertion text NOT NULL CHECK (assertion IN ('occurred', 'stated', 'attempted', 'believed')),
    speaker_entity_id uuid NULL REFERENCES memory_entity (entity_id) ON DELETE SET NULL,
    valid_from_seq integer NOT NULL,
    authored_fact_id uuid NULL,
    is_hidden boolean NOT NULL DEFAULT false,
    conditional boolean NOT NULL DEFAULT false,
    extraction_batch_id uuid NULL
        REFERENCES memory_extraction_batch (batch_id) ON DELETE SET NULL,
    event_id uuid NULL REFERENCES memory_event (event_id) ON DELETE SET NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX memory_fact_scope_valid_from_idx ON memory_fact (scope_kind, scope_id, valid_from_seq);
CREATE UNIQUE INDEX memory_fact_scope_authored_fact_key
    ON memory_fact (scope_kind, scope_id, authored_fact_id)
    WHERE authored_fact_id IS NOT NULL;
CREATE INDEX memory_fact_scope_subject_predicate_idx
    ON memory_fact (scope_kind, scope_id, subject_entity_id, predicate);
CREATE INDEX memory_fact_scope_object_predicate_idx
    ON memory_fact (scope_kind, scope_id, object_entity_id, predicate);
CREATE INDEX memory_fact_subject_entity_idx ON memory_fact (subject_entity_id);
CREATE INDEX memory_fact_object_entity_idx ON memory_fact (object_entity_id)
    WHERE object_entity_id IS NOT NULL;
CREATE INDEX memory_fact_speaker_entity_idx ON memory_fact (speaker_entity_id)
    WHERE speaker_entity_id IS NOT NULL;
CREATE INDEX memory_fact_extraction_batch_idx ON memory_fact (extraction_batch_id)
    WHERE extraction_batch_id IS NOT NULL;
CREATE INDEX memory_fact_event_idx ON memory_fact (event_id)
    WHERE event_id IS NOT NULL;

CREATE TABLE memory_fact_source (
    fact_id uuid NOT NULL REFERENCES memory_fact (fact_id) ON DELETE CASCADE,
    span_id uuid NOT NULL REFERENCES memory_span (span_id) ON DELETE CASCADE,
    PRIMARY KEY (fact_id, span_id)
);

CREATE INDEX memory_fact_source_span_idx ON memory_fact_source (span_id);

CREATE TABLE memory_supersession (
    supersession_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    playthrough_id uuid NOT NULL
        REFERENCES memory_playthrough (playthrough_id) ON DELETE CASCADE,
    fact_id uuid NOT NULL REFERENCES memory_fact (fact_id) ON DELETE CASCADE,
    at_seq integer NOT NULL,
    superseding_fact_id uuid NULL REFERENCES memory_fact (fact_id) ON DELETE SET NULL,
    authority text NOT NULL CHECK (authority IN ('authored', 'accepted', 'extracted')),
    evidence_span_id uuid NULL REFERENCES memory_span (span_id) ON DELETE SET NULL,
    extraction_batch_id uuid NULL
        REFERENCES memory_extraction_batch (batch_id) ON DELETE SET NULL,
    event_id uuid NULL REFERENCES memory_event (event_id) ON DELETE SET NULL,
    CONSTRAINT memory_supersession_playthrough_fact_seq_key
        UNIQUE (playthrough_id, fact_id, at_seq)
);

CREATE INDEX memory_supersession_fact_idx ON memory_supersession (fact_id);
CREATE INDEX memory_supersession_superseding_fact_idx ON memory_supersession (superseding_fact_id)
    WHERE superseding_fact_id IS NOT NULL;

-- Commitments and scene ------------------------------------------------------

CREATE TABLE memory_commitment (
    commitment_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    playthrough_id uuid NOT NULL
        REFERENCES memory_playthrough (playthrough_id) ON DELETE CASCADE,
    kind text NOT NULL CHECK (kind IN ('promise', 'debt', 'quest', 'threat')),
    owner_entity_id uuid NOT NULL REFERENCES memory_entity (entity_id) ON DELETE CASCADE,
    counterparty_entity_id uuid NULL REFERENCES memory_entity (entity_id) ON DELETE SET NULL,
    summary text NOT NULL,
    opened_seq integer NOT NULL,
    opening_span_id uuid NOT NULL REFERENCES memory_span (span_id) ON DELETE CASCADE,
    extraction_batch_id uuid NOT NULL
        REFERENCES memory_extraction_batch (batch_id) ON DELETE CASCADE
);

CREATE INDEX memory_commitment_playthrough_opened_idx
    ON memory_commitment (playthrough_id, opened_seq);
CREATE INDEX memory_commitment_owner_entity_idx ON memory_commitment (owner_entity_id);

CREATE TABLE memory_commitment_status (
    commitment_id uuid NOT NULL
        REFERENCES memory_commitment (commitment_id) ON DELETE CASCADE,
    at_seq integer NOT NULL,
    status text NOT NULL CHECK (status IN ('open', 'fulfilled', 'broken', 'cancelled')),
    evidence_span_id uuid NULL REFERENCES memory_span (span_id) ON DELETE SET NULL,
    event_id uuid NULL REFERENCES memory_event (event_id) ON DELETE SET NULL,
    extraction_batch_id uuid NULL
        REFERENCES memory_extraction_batch (batch_id) ON DELETE SET NULL,
    PRIMARY KEY (commitment_id, at_seq)
);

CREATE TABLE memory_scene_state (
    playthrough_id uuid NOT NULL
        REFERENCES memory_playthrough (playthrough_id) ON DELETE CASCADE,
    valid_from_seq integer NOT NULL,
    location_entity_id uuid NULL REFERENCES memory_entity (entity_id) ON DELETE SET NULL,
    present_entity_ids uuid[] NOT NULL,
    extraction_batch_id uuid NOT NULL
        REFERENCES memory_extraction_batch (batch_id) ON DELETE CASCADE,
    PRIMARY KEY (playthrough_id, valid_from_seq)
);

-- Embeddings -----------------------------------------------------------------

CREATE TABLE memory_embedding_model (
    model text NOT NULL,
    model_version text NOT NULL,
    dim integer NOT NULL CHECK (dim > 0),
    is_active boolean NOT NULL,
    PRIMARY KEY (model, model_version),
    CONSTRAINT memory_embedding_model_dim_key UNIQUE (model, model_version, dim)
);

CREATE UNIQUE INDEX memory_embedding_model_single_active_idx
    ON memory_embedding_model ((true)) WHERE is_active;

CREATE TABLE memory_embedding (
    target_kind text NOT NULL CHECK (target_kind IN ('span', 'fact')),
    target_id uuid NOT NULL,
    scope_kind text NOT NULL CHECK (scope_kind IN ('template', 'playthrough')),
    scope_id uuid NOT NULL,
    model text NOT NULL,
    model_version text NOT NULL,
    dim integer NOT NULL,
    embedding vector NOT NULL,
    content_hash text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (target_kind, target_id, model, model_version),
    CONSTRAINT memory_embedding_dim_check CHECK (vector_dims(embedding) = dim),
    CONSTRAINT memory_embedding_model_fkey FOREIGN KEY (model, model_version, dim)
        REFERENCES memory_embedding_model (model, model_version, dim) ON DELETE CASCADE
);

CREATE INDEX memory_embedding_scope_model_idx
    ON memory_embedding (scope_kind, scope_id, model, model_version);
CREATE INDEX memory_embedding_model_idx ON memory_embedding (model, model_version, dim);

-- 0006_extraction_context: participant display names and master tracked fields for the
-- extraction prompt, and a stable error code for failed template enrichment.

ALTER TABLE memory_playthrough
    ADD COLUMN participants jsonb NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN tracked_fields text[] NOT NULL DEFAULT '{}';

ALTER TABLE memory_template
    ADD COLUMN enrichment_error text NULL;

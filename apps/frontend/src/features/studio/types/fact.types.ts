export interface FactCreate {
  subject_entity_id: string;
  predicate: string;
  object_entity_id?: string;
  object_literal?: string;
  valid_from?: string;
  when_active?: Record<string, unknown>;
  hidden?: boolean;
  superseded_fact_id?: string;
  expected_content_edited_at?: string;
}

export interface FactUpdate {
  predicate?: string;
  object_entity_id?: string;
  object_literal?: string;
  valid_from?: string;
  when_active?: Record<string, unknown> | null;
  hidden?: boolean;
  superseded_fact_id?: string;
  expected_content_edited_at?: string;
}

export interface FactResponse {
  fact_id: string;
  scenario_id: string;
  subject_entity_id: string;
  predicate: string;
  object_entity_id: string | null;
  object_literal: string | null;
  valid_from: string | null;
  when_active: Record<string, unknown> | null;
  hidden: boolean;
  superseded_fact_id: string | null;
  scenario_content_edited_at?: string | null;
}

export interface FactListResponse {
  items: FactResponse[];
}

export interface NewLinkInput {
  predicate: string;
  otherEntityId?: string;
  objectLiteral?: string;
  whenActive?: Record<string, unknown>;
}

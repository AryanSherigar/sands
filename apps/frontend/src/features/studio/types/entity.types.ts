import type { LoreDocument } from "./lore.types";

export const ENTITY_TYPES = [
  "character",
  "location",
  "item",
  "faction",
  "organization",
] as const;

export type AttributeFieldType = "string" | "number" | "boolean" | "enum";

export interface AttributeFieldSchema {
  type: AttributeFieldType;
  initial?: unknown;
  min?: number;
  max?: number;
  label?: string;
  is_narrator_visible?: boolean;
}

export interface EntityCreate {
  entity_type: string;
  canonical_name: string;
  aliases?: string[];
  description?: string;
  obtainable?: boolean;
  attributes_schema?: Record<string, AttributeFieldSchema>;
  narrator_instruction?: string;
  is_player?: boolean;
  lore_document?: LoreDocument | null;
  expected_content_edited_at?: string;
}

export interface EntityUpdate {
  entity_type?: string;
  canonical_name?: string;
  aliases?: string[];
  description?: string;
  obtainable?: boolean;
  attributes_schema?: Record<string, AttributeFieldSchema>;
  narrator_instruction?: string;
  is_player?: boolean;
  lore_document?: LoreDocument | null;
  expected_content_edited_at?: string;
}

export interface EntityResponse {
  entity_id: string;
  scenario_id: string;
  entity_type: string;
  canonical_name: string;
  aliases: string[];
  description: string | null;
  obtainable: boolean | null;
  attributes_schema: Record<string, AttributeFieldSchema>;
  narrator_instruction: string | null;
  is_player?: boolean;
  fact_count?: number;
  lore_document?: LoreDocument | null;
  scenario_content_edited_at?: string | null;
}

export interface EntityListResponse {
  items: EntityResponse[];
}

export interface EntityTypeChangePreviewRequest {
  new_entity_type: string;
}

export interface EntityTypeChangePreviewResponse {
  dropped_fields: string[];
  retained_fields: string[];
  added_fields: string[];
}

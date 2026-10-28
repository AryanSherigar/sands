export type FeedbackCategory = "bug" | "confusing" | "scary" | "other";

export type FlagReason =
  | "broke_rule"
  | "contradicted"
  | "out_of_character"
  | "too_long"
  | "other";

export interface AlphaFeedbackRequest {
  playthrough_id: string;
  turn_number: number | null;
  category: FeedbackCategory;
  body: string;
}

export interface AlphaFlagRequest {
  reasons: FlagReason[];
  note?: string;
}

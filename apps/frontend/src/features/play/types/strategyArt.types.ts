export type StrategyArtKind = "event" | "uprising" | "chronicle";

export type StrategyArtStatus = "pending" | "generating" | "completed" | "failed";

export interface StrategyArtView {
  kind: StrategyArtKind;
  item_id: string;
  status: StrategyArtStatus;
  art_url: string | null;
  error_code: string | null;
  is_retryable: boolean;
}

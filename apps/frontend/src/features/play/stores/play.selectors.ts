interface RetryableState {
  is_narrating: boolean;
  last_client_action_id: string | null;
  last_check_report: unknown;
}

/** Retry is for recovery only: after a saved turn the id is cleared, and a
 * retry would then spend quota on a brand-new turn with the same text. */
export function selectCanRetryTurn(state: RetryableState): boolean {
  if (state.is_narrating) return false;
  return state.last_client_action_id !== null || state.last_check_report !== null;
}

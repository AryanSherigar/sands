interface PlaythroughProgress {
  playthrough_id: string;
  turns: readonly unknown[];
}

// A refetch can arrive before the server has the turn just committed locally;
// applying it would erase that turn. That only holds for the same playthrough:
// a different one (a new run started from inside the app) always replaces it.
export function shouldApplyServerPlaythrough(
  current: PlaythroughProgress | null,
  incoming: PlaythroughProgress,
): boolean {
  if (current === null) return true;
  if (current.playthrough_id !== incoming.playthrough_id) return true;
  return incoming.turns.length >= current.turns.length;
}

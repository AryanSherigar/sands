const STORAGE_PREFIX = "sands:chronicler-attribution:";

type AttributionMap = Record<string, string>;

const storageKey = (playthroughId: string): string => `${STORAGE_PREFIX}${playthroughId}`;

export function readChroniclerAttribution(playthroughId: string | undefined): AttributionMap {
  if (!playthroughId) return {};
  try {
    const raw = window.localStorage.getItem(storageKey(playthroughId));
    return raw ? (JSON.parse(raw) as AttributionMap) : {};
  } catch {
    return {};
  }
}

export function recordChroniclerAttribution(
  playthroughId: string | undefined,
  summaryId: string,
  chroniclerId: string,
): AttributionMap {
  const next = { ...readChroniclerAttribution(playthroughId), [summaryId]: chroniclerId };
  if (!playthroughId) return next;
  try {
    window.localStorage.setItem(storageKey(playthroughId), JSON.stringify(next));
  } catch {
    // NOTE: attribution is a per-viewer convenience; losing it only drops the name label.
  }
  return next;
}

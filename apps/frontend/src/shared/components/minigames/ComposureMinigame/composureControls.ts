import type { ComposureKey } from "@/shared/types/minigame.types";

// Matched by physical key position (`event.code`), so W/A/S/D works on AZERTY
// and Dvorak too; the arrow keys share the same four slots.
const CODE_TO_KEY: Record<string, ComposureKey> = {
  KeyW: "W",
  ArrowUp: "W",
  KeyA: "A",
  ArrowLeft: "A",
  KeyS: "S",
  ArrowDown: "S",
  KeyD: "D",
  ArrowRight: "D",
};

export const KEY_ARROW_GLYPHS: Record<ComposureKey, string> = {
  W: "↑",
  A: "←",
  S: "↓",
  D: "→",
};

export const keyFromCode = (code: string): ComposureKey | null =>
  CODE_TO_KEY[code] ?? null;

interface KeyTarget {
  addEventListener: (type: "keydown", listener: (event: KeyboardEvent) => void) => void;
  removeEventListener: (type: "keydown", listener: (event: KeyboardEvent) => void) => void;
}

// `keydown` only; auto-repeat and keys outside the scenario's set are ignored.
export function attachComposureControls(
  target: KeyTarget,
  allowedKeys: ComposureKey[],
  onPress: (key: ComposureKey, eventTimeStampMs: number) => void,
): () => void {
  const handleKeyDown = (event: KeyboardEvent): void => {
    const key = keyFromCode(event.code);
    if (key === null || !allowedKeys.includes(key)) return;
    event.preventDefault();
    if (event.repeat) return;
    onPress(key, event.timeStamp);
  };
  target.addEventListener("keydown", handleKeyDown);
  return () => target.removeEventListener("keydown", handleKeyDown);
}

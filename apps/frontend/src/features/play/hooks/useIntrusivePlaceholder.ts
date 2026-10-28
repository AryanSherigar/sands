import { useEffect, useState } from "react";
import { useSanityBand } from "./useSanityBand";

export const INTRUSIVE_INTERVAL_MS = 7000;

export interface IntrusivePlaceholder {
  placeholder: string;
  isIntrusive: boolean;
}

// While the meter is below `intrusive_below`, the input's placeholder alternates
// every 7 s between the standard text and the creator's phrases, in the order
// they were authored. Typing (`isSuppressed`) removes it, and a change of
// `restartToken` (the input gaining focus) restores the standard text at once and
// restarts the alternation.
// NOTE: The action drawer focuses its input as soon as it opens, so suppressing
// the effect for as long as the input is focused would hide it entirely.
export function useIntrusivePlaceholder(
  standardPlaceholder: string,
  isSuppressed: boolean,
  restartToken: number,
): IntrusivePlaceholder {
  const { value, effects } = useSanityBand();
  const thoughts = effects?.intrusive_thoughts ?? [];
  const threshold = effects?.intrusive_below;
  const isArmed =
    value !== null &&
    threshold !== undefined &&
    value < threshold &&
    thoughts.length > 0 &&
    !isSuppressed;
  const [step, setStep] = useState(0);

  useEffect(() => {
    setStep(0);
    if (!isArmed) return undefined;
    const timer = setInterval(() => setStep((current) => current + 1), INTRUSIVE_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [isArmed, restartToken]);

  const isIntrusive = isArmed && step % 2 === 1;
  if (!isIntrusive) return { placeholder: standardPlaceholder, isIntrusive: false };
  const phrase = thoughts[Math.floor(step / 2) % thoughts.length];
  return { placeholder: phrase, isIntrusive: true };
}

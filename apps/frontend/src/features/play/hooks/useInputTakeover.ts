import { useEffect, useState } from "react";
import { useIsMotionReduced } from "@/shared/hooks/useIsMotionReduced";
import type { InputTakeoverParams } from "@/shared/lib/client-effects/clientEffects.types";
import { usePlayStore } from "../stores/play.store";

export interface InputTakeover {
  takeoverText: string | null;
  isLocked: boolean;
}

const IDLE: InputTakeover = { takeoverText: null, isLocked: false };

type Show = (view: InputTakeover) => void;
type Timers = { clear: () => void };

function showStill(params: InputTakeoverParams, show: Show, end: () => void): Timers {
  show({ takeoverText: params.text, isLocked: false });
  const timer = setTimeout(end, params.lock_ms);
  return { clear: () => clearTimeout(timer) };
}

function typeThenLock(params: InputTakeoverParams, show: Show, end: () => void): Timers {
  let typed = 0;
  let lockTimer: ReturnType<typeof setTimeout> | undefined;
  const typing = setInterval(() => {
    typed += 1;
    show({ takeoverText: params.text.slice(0, typed), isLocked: true });
    if (typed < params.text.length) return;
    clearInterval(typing);
    lockTimer = setTimeout(end, params.lock_ms);
  }, params.type_ms_per_char);
  show({ takeoverText: "", isLocked: true });
  return {
    clear: () => {
      clearInterval(typing);
      clearTimeout(lockTimer);
    },
  };
}

// While an `input_takeover` client effect is active, the action input is not
// the player's: a line types itself into the placeholder and the input stays
// locked for `lock_ms`, then the effect finishes and the input is theirs again.
export function useInputTakeover(): InputTakeover {
  const effect = usePlayStore((s) => s.active_client_effect);
  const finishClientEffect = usePlayStore((s) => s.finishClientEffect);
  const openActionDrawer = usePlayStore((s) => s.openActionDrawer);
  const isMotionReduced = useIsMotionReduced();
  const [view, setView] = useState<InputTakeover>(IDLE);
  const params = effect?.kind === "input_takeover" ? effect.params : null;

  useEffect(() => {
    if (!params) return undefined;
    openActionDrawer();
    const end = () => {
      setView(IDLE);
      finishClientEffect();
    };
    const run = isMotionReduced ? showStill : typeThenLock;
    const timers = run(params, setView, end);
    return () => timers.clear();
  }, [params, isMotionReduced, openActionDrawer, finishClientEffect]);

  return params ? view : IDLE;
}

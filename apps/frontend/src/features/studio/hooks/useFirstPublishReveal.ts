import { useCallback, useEffect, useRef, useState } from "react";
import { logEvent } from "@/shared/lib/logger";
import { fetchMyAchievements } from "../api/achievements.api";
import {
  ACHIEVEMENT_CHECK_ATTEMPTS,
  ACHIEVEMENT_CHECK_INTERVAL_MS,
} from "../constants/achievements";
import { findWorldmaker, isEarned } from "../lib/worldmaker";
import type { AchievementSummary } from "../types/achievement.types";

const wait = (milliseconds: number): Promise<void> =>
  new Promise((resolve) => setTimeout(resolve, milliseconds));

const findNewlyEarned = async (
  isCancelled: () => boolean,
): Promise<AchievementSummary | null> => {
  for (let attempt = 0; attempt < ACHIEVEMENT_CHECK_ATTEMPTS; attempt += 1) {
    const worldmaker = findWorldmaker(await fetchMyAchievements());
    if (isEarned(worldmaker)) return worldmaker;
    await wait(ACHIEVEMENT_CHECK_INTERVAL_MS);
    if (isCancelled()) return null;
  }
  return null;
};

export const useFirstPublishReveal = (hasJustPublished: boolean) => {
  const wasEarnedBeforeRef = useRef<boolean | null>(null);
  const [achievement, setAchievement] = useState<AchievementSummary | null>(null);

  const recordBaseline = useCallback(async (): Promise<void> => {
    try {
      wasEarnedBeforeRef.current = isEarned(findWorldmaker(await fetchMyAchievements()));
    } catch (error) {
      wasEarnedBeforeRef.current = null;
      logEvent("warning", "worldmaker_baseline_failed", { error: String(error) });
    }
  }, []);

  useEffect(() => {
    if (!hasJustPublished || wasEarnedBeforeRef.current !== false) return undefined;
    let isCancelled = false;
    findNewlyEarned(() => isCancelled)
      .then((earned) => {
        if (!isCancelled) setAchievement(earned);
      })
      .catch((error: unknown) =>
        logEvent("warning", "worldmaker_check_failed", { error: String(error) }),
      );
    return () => {
      isCancelled = true;
    };
  }, [hasJustPublished]);

  return { recordBaseline, achievement };
};

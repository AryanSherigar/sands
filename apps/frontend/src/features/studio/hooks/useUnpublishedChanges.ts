import { useEffect, useRef, useState } from "react";
import {
  countUnpublishedChanges,
  hasServerUnpublishedChanges,
} from "../lib/unpublishedChanges";
import type { ScenarioResponse } from "../types/scenario.types";

export const useUnpublishedChanges = (scenario: ScenarioResponse | null): number => {
  const [sessionEditCount, setSessionEditCount] = useState(0);
  const lastStampRef = useRef<string | undefined>(undefined);
  const isLive = scenario?.status === "published";
  const stamp = scenario?.content_edited_at;
  const publishedAt = scenario?.published_at;

  useEffect(() => {
    setSessionEditCount(0);
  }, [publishedAt, isLive]);

  useEffect(() => {
    const previous = lastStampRef.current;
    lastStampRef.current = stamp;
    if (isLive && previous && stamp && previous !== stamp) {
      setSessionEditCount((count) => count + 1);
    }
  }, [isLive, stamp]);

  return countUnpublishedChanges(sessionEditCount, hasServerUnpublishedChanges(scenario));
};

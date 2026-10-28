import React from "react";
import { Button } from "@/shared/components/ui/Button";
import { PLAYTEST_STALE_MESSAGE } from "../../constants/playtest";
import type { PlaytestStaleBannerProps } from "./PlaytestTab.types";

export const PlaytestStaleBanner: React.FC<PlaytestStaleBannerProps> = ({ onKeepPlaying }) => (
  <div role="status" className="flex flex-wrap items-center justify-between gap-2 border-b border-border-subtle bg-surface-raised px-4 py-2 text-meta text-content-muted">
    <span>{PLAYTEST_STALE_MESSAGE}</span>
    <Button type="button" variant="ghost" size="sm" onClick={onKeepPlaying}>
      Keep playing
    </Button>
  </div>
);

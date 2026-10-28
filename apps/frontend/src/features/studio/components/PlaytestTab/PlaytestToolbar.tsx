import React from "react";
import { Button } from "@/shared/components/ui/Button";
import { PLAYTEST_LABEL } from "../../constants/playtest";
import type { PlaytestToolbarProps } from "./PlaytestTab.types";

export const PlaytestToolbar: React.FC<PlaytestToolbarProps> = ({ isBusy, onRestart, onEnd }) => (
  <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border-subtle px-4 py-2">
    <p className="text-meta text-content-muted">{PLAYTEST_LABEL}</p>
    <div className="flex items-center gap-2">
      <Button type="button" variant="secondary" size="sm" disabled={isBusy} onClick={onRestart}>
        Restart with my changes
      </Button>
      <Button type="button" variant="ghost" size="sm" onClick={onEnd}>
        End playtest
      </Button>
    </div>
  </div>
);

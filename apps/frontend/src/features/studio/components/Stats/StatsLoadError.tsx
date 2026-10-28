import React from "react";
import { Button } from "@/shared/components/ui/Button";
import { StatsNotice } from "./StatsNotice";
import type { StatsLoadErrorProps } from "./StatsLoadError.types";

export const StatsLoadError: React.FC<StatsLoadErrorProps> = ({ onRetry }) => (
  <StatsNotice title="Couldn't load stats" description="Something went wrong on our side.">
    <Button variant="secondary" onClick={onRetry}>
      Retry
    </Button>
  </StatsNotice>
);

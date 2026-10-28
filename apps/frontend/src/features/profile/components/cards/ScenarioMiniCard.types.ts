import type React from "react";
import type { ScenarioSummaryResponse } from "@/features/play/types/scenario";

export interface ScenarioMiniCardProps {
  scenario: ScenarioSummaryResponse;
  overlayAction?: React.ReactNode;
  footerAction?: React.ReactNode;
}

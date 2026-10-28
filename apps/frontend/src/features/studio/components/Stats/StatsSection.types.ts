import type React from "react";
import type { StatsSectionLink } from "../../types/statsView.types";

export interface StatsSectionProps {
  section: StatsSectionLink;
  children: React.ReactNode;
}

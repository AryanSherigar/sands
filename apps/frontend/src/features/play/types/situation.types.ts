export type SituationSeverityStage = 1 | 2 | 3 | 4;

export type SituationSource = "event" | "uprising";

export interface SituationInterventionLever {
  source?: SituationSource;
  id: string;
  label: string;
  orderCost: number;
  eventId: string;
  choiceId: string;
  effects: string[];
  isAffordable: boolean;
  isQueued: boolean;
  queuedCommandId?: string | null;
}

export interface ActiveSituation {
  source?: SituationSource;
  id: string;
  eventId: string | null;
  title: string;
  regionId: string | null;
  regionName: string;
  subheading: string;
  severityStage: SituationSeverityStage;
  maxStage: SituationSeverityStage;
  severityLabel: string;
  stageLabels: string[];
  causeQuote: string;
  intelligence: string[];
  ifIgnoredWarning: string | null;
  deadlineTurn: number | null;
  scar: number;
  isActionable: boolean;
  levers: SituationInterventionLever[];
}

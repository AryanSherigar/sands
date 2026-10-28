export interface EventCharacter {
  name: string;
  title: string;
  disposition: string;
  avatarUrl?: string;
}

export interface EventChoice {
  id: string;
  label: string;
  effects: string[];
  isMapOrder?: boolean;
  orderCost?: number;
  isAffordable?: boolean;
}

export interface StrategyEventPackage {
  sceneId: string;
  category: "trouble" | "good_news";
  title: string;
  subheading: string;
  turnText: string;
  bodyProse: string;
  causeQuote: string;
  character: EventCharacter;
  choices: EventChoice[];
  eventId?: string;
  source?: "event" | "uprising";
  neglectWarning?: string;
  queuedChoiceId?: string | null;
  queuedCommandId?: string | null;
}

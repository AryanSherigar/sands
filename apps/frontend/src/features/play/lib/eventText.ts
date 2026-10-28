import type {
  EffectPreviewView,
  EventMemoryView,
  PendingEventView,
} from "../types/simulation.types";
import type { SituationSeverityStage } from "../types/situation.types";

const MINUS = "−";
const MAX_STAGE = 4;

const EFFECT_LABELS: Record<string, string> = {
  gold: "Gold",
  unrest: "Unrest (all regions)",
  region_unrest: "Unrest",
  stability: "Stability",
  manpower: "Manpower",
  reputation: "Reputation",
  governor_opinion: "Governor opinion",
  army_morale: "Army morale",
};

const CAUSE_PHRASES: Record<string, (value: number) => string> = {
  region_unrest: (value) => `unrest is ${value}`,
  governor_opinion: (value) => `the governor's opinion of you is ${signed(value)}`,
  army_unpaid_turns: (value) => `pay is ${value} ${value === 1 ? "turn" : "turns"} overdue`,
  army_morale: (value) => `morale is ${value}`,
  regions_with_unrest_at_least: (value) =>
    `${value} ${value === 1 ? "province is" : "provinces are"} in open unrest`,
  stability: (value) => `stability is ${value}`,
  treasury: (value) => `the treasury holds ${value}`,
  war_exhaustion: (value) => `war exhaustion is ${value}`,
};

interface TemplateText {
  stageLabels: string[];
  title: (subject: string) => string;
  subheading: string;
  body: (subject: string) => string;
  characterTitle: string;
  dispositions: string[];
}

const TEMPLATE_TEXT: Record<string, TemplateText> = {
  tax_grievance: {
    stageLabels: ["Murmurs", "Petition", "Revolt looms"],
    title: (subject) => `Grievance in ${subject}`,
    subheading: "Provincial Domain",
    body: (subject) => `The levies weigh heavily on ${subject}, and its people are making their anger known.`,
    characterTitle: "Provincial petitioners",
    dispositions: ["Uneasy", "Angry", "Defiant"],
  },
  noble_defiance: {
    stageLabels: ["Resentful", "Defiant", "On the brink"],
    title: (subject) => `${subject} defies the crown`,
    subheading: "Noble Court",
    body: (subject) => `${subject} no longer hides contempt for your rule and is testing how far it can go.`,
    characterTitle: "Lord of the province",
    dispositions: ["Resentful", "Defiant", "Hostile"],
  },
  unpaid_mutiny: {
    stageLabels: ["Grumbling", "Mutinous", "Open mutiny"],
    title: (subject) => `Unpaid troops: ${subject}`,
    subheading: "The Soldiery",
    body: (subject) => `The soldiers of ${subject} have gone without pay and are talking of taking what is owed.`,
    characterTitle: "Soldiers' council",
    dispositions: ["Restless", "Mutinous", "Rebellious"],
  },
  realm_in_turmoil: {
    stageLabels: ["Stirring", "Widespread unrest", "Realm in turmoil"],
    title: () => "The realm stirs",
    subheading: "Crown Council",
    body: () => "Trouble in several provinces at once has the council fearing it will not stay local.",
    characterTitle: "Royal council",
    dispositions: ["Anxious", "Alarmed", "Desperate"],
  },
};

const FALLBACK_TEXT: TemplateText = {
  stageLabels: [],
  title: (subject) => subject,
  subheading: "Crown Jurisdiction",
  body: (subject) => `A matter concerning ${subject} requires your decision.`,
  characterTitle: "Envoy",
  dispositions: [],
};

function signed(value: number): string {
  return value < 0 ? `${MINUS}${Math.abs(value)}` : `${value}`;
}

function textFor(templateId: string): TemplateText {
  return TEMPLATE_TEXT[templateId] ?? FALLBACK_TEXT;
}

export function stageLabel(templateId: string, stage: number): string {
  return textFor(templateId).stageLabels[stage - 1] ?? `Stage ${stage}`;
}

export function stageLabels(templateId: string, maxStage: number): string[] {
  return Array.from({ length: maxStage }, (_, index) => stageLabel(templateId, index + 1));
}

export function toStage(tier: number): SituationSeverityStage {
  return Math.min(Math.max(tier, 1), MAX_STAGE) as SituationSeverityStage;
}

export function describeEffect(effect: EffectPreviewView): string {
  const label = EFFECT_LABELS[effect.kind] ?? effect.kind.replace(/_/g, " ");
  const sign = effect.amount < 0 ? MINUS : "+";
  return `${label} ${sign}${Math.abs(effect.amount)}`;
}

export function describeEffects(effects: EffectPreviewView[]): string[] {
  return effects.map(describeEffect);
}

export function describeCause(causeInputs: Record<string, number>): string {
  const phrases = Object.entries(causeInputs)
    .filter(([key]) => key in CAUSE_PHRASES)
    .map(([key, value]) => CAUSE_PHRASES[key](value));
  return phrases.length > 0 ? `Because ${phrases.join(" and ")}.` : "";
}

export function describeIntelligence(causeInputs: Record<string, number>): string[] {
  return Object.entries(causeInputs)
    .filter(([key]) => key in CAUSE_PHRASES)
    .map(([key, value]) => {
      const phrase = CAUSE_PHRASES[key](value);
      return phrase.charAt(0).toUpperCase() + phrase.slice(1);
    });
}

export function describeNeglect(effects: EffectPreviewView[]): string {
  return effects.length > 0 ? describeEffects(effects).join(", ") : "";
}

export interface EventNarrative {
  title: string;
  subheading: string;
  bodyProse: string;
  causeQuote: string;
  characterName: string;
  characterTitle: string;
  disposition: string;
}

export function narrate(event: PendingEventView): EventNarrative {
  const text = textFor(event.template_id);
  return {
    title: text.title(event.subject_name),
    subheading: text.subheading,
    bodyProse: text.body(event.subject_name),
    causeQuote: describeCause(event.cause_inputs),
    characterName: event.subject_name,
    characterTitle: text.characterTitle,
    disposition: text.dispositions[event.tier - 1] ?? "Troubled",
  };
}

export function eventTitle(templateId: string, subjectName: string): string {
  return textFor(templateId).title(subjectName);
}

export function memoryTitle(memory: EventMemoryView): string {
  return textFor(memory.template_id).title(memory.subject_name);
}

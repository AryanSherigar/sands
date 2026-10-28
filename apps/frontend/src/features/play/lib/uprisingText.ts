import { describeEffects } from "./eventText";
import type {
  UprisingArchetype,
  UprisingResponseId,
  UprisingStage,
  UprisingView,
} from "../types/simulation.types";
import type { SituationSeverityStage } from "../types/situation.types";

const STAGE_NUMBER: Record<UprisingStage, SituationSeverityStage> = {
  unrest: 1,
  riot: 2,
  armed: 3,
};
export const UPRISING_MAX_STAGE: SituationSeverityStage = 3;

interface ArchetypeText {
  stageLabels: string[];
  title: (region: string) => string;
  subheading: string;
  body: (region: string) => string;
  characterTitle: string;
  dispositions: string[];
}

const ARCHETYPE_TEXT: Record<UprisingArchetype, ArchetypeText> = {
  petition: {
    stageLabels: ["Petition", "Rioting", "Armed revolt"],
    title: (region) => `Petition from ${region}`,
    subheading: "Provincial Domain",
    body: (region) =>
      `A delegation from ${region} stands before you with demands. They have not yet raised their hands against the crown.`,
    characterTitle: "Spokesman of the petitioners",
    dispositions: ["Aggrieved", "Furious", "Defiant"],
  },
  riot: {
    stageLabels: ["Murmurs", "Rioting", "Armed revolt"],
    title: (region) => `Riot in ${region}`,
    subheading: "Provincial Domain",
    body: (region) =>
      `The streets of ${region} are full, and no one speaks for the crowd. There is no one to bargain with, only order to keep.`,
    characterTitle: "The crowd",
    dispositions: ["Angry", "Violent", "Armed"],
  },
  rebellion: {
    stageLabels: ["Conspiracy", "Rising", "Armed revolt"],
    title: (region) => `Rebellion in ${region}`,
    subheading: "Provincial Domain",
    body: (region) =>
      `${region} has risen in arms. Whatever grievance began this, the time for talking has largely passed.`,
    characterTitle: "Rebel captain",
    dispositions: ["Resolute", "Resolute", "Ruthless"],
  },
};

const RESPONSE_LABELS: Record<UprisingResponseId, string> = {
  concessions: "Grant their demands",
  restore_order: "Restore order by force",
  negotiate: "Hear them out",
};

export function uprisingStage(stage: UprisingStage): SituationSeverityStage {
  return STAGE_NUMBER[stage];
}

export function responseLabel(response: UprisingResponseId): string {
  return RESPONSE_LABELS[response];
}

export function uprisingText(archetype: UprisingArchetype): ArchetypeText {
  return ARCHETYPE_TEXT[archetype];
}

export function describeUprisingCause(uprising: UprisingView, regionName: string): string {
  return `Because unrest in ${regionName} reached ${uprising.trigger_unrest}.`;
}

export function describeUprisingIntelligence(uprising: UprisingView): string[] {
  const rebels =
    uprising.rebel_troops === null ? [] : [`Rebels hold the region with ${uprising.rebel_troops} men`];
  return [
    ...rebels,
    `Local income −${uprising.income_penalty_percent}%`,
    `Local manpower −${uprising.manpower_penalty_percent}%`,
    `Supply capacity −${uprising.supply_penalty_percent}%`,
    uprising.is_easing
      ? "A garrison or lighter taxes are easing the pressure."
      : "Nothing is easing the pressure.",
  ];
}

export function describeUprisingNeglect(uprising: UprisingView): string {
  const turns = uprising.turns_until_change;
  const wait = turns === 1 ? "next turn" : `within ${turns} turns`;
  if (uprising.is_final_stage) {
    return `If unanswered ${wait}, the region will be lost to the crown.`;
  }
  const next = ARCHETYPE_TEXT[uprising.archetype].stageLabels[uprisingStage(uprising.stage)];
  return `If unanswered ${wait}, it will worsen to ${next.toLowerCase()}.`;
}

export function describeResponseEffects(
  response: UprisingView["responses"][number],
): string[] {
  return [...describeEffects(response.effects), ...response.notes];
}

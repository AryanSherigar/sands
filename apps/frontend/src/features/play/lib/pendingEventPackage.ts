import { describeEffects, describeNeglect, narrate } from "./eventText";
import type { StrategyEventPackage } from "../types/eventScene.types";
import { describeResponseEffects, describeUprisingCause, describeUprisingNeglect, responseLabel, uprisingStage, uprisingText } from "./uprisingText";
import type { CampaignWorldView, UprisingView } from "../types/simulation.types";

function buildUprisingPackage(
  world: CampaignWorldView,
  uprising: UprisingView,
  regionNames: Record<string, string>,
): StrategyEventPackage {
  const regionName = regionNames[uprising.region_id] ?? uprising.region_id;
  const text = uprisingText(uprising.archetype);
  const year = world.clock?.start_year;
  return {
    sceneId: uprising.id,
    eventId: uprising.id,
    source: "uprising",
    category: "trouble",
    title: text.title(regionName),
    subheading: text.subheading,
    turnText: year === undefined ? `Turn ${world.turn}` : `Turn ${world.turn} • Year ${year}`,
    bodyProse: text.body(regionName),
    causeQuote: describeUprisingCause(uprising, regionName),
    character: {
      name: regionName,
      title: text.characterTitle,
      disposition: text.dispositions[uprisingStage(uprising.stage) - 1],
    },
    choices: uprising.responses.map((response) => ({
      id: response.id,
      label: responseLabel(response.id),
      effects: describeResponseEffects(response),
      orderCost: response.order_cost,
      isAffordable: response.is_affordable,
    })),
    neglectWarning: describeUprisingNeglect(uprising),
    queuedChoiceId: uprising.queued_response,
    queuedCommandId: uprising.queued_command_id,
  };
}

export function buildPendingEventPackage(
  world: CampaignWorldView,
  eventId: string | null,
  regionNames: Record<string, string> = {},
): StrategyEventPackage | null {
  const uprising = eventId ? world.uprisings?.find((item) => item.id === eventId) : undefined;
  if (uprising) return buildUprisingPackage(world, uprising, regionNames);
  const event = eventId ? world.pending_events?.find((item) => item.id === eventId) : undefined;
  if (!event) return null;
  const narrative = narrate(event);
  const year = world.clock?.start_year;
  return {
    sceneId: event.id,
    eventId: event.id,
    category: "trouble",
    title: narrative.title,
    subheading: narrative.subheading,
    turnText: year === undefined ? `Turn ${world.turn}` : `Turn ${world.turn} • Year ${year}`,
    bodyProse: narrative.bodyProse,
    causeQuote: narrative.causeQuote,
    character: {
      name: narrative.characterName,
      title: narrative.characterTitle,
      disposition: narrative.disposition,
    },
    choices: event.choices.map((choice) => ({
      id: choice.id,
      label: choice.label_hint,
      effects: describeEffects(choice.effects),
      orderCost: choice.order_cost,
      isAffordable: choice.is_affordable,
    })),
    neglectWarning: describeNeglect(event.neglect_effects),
    queuedChoiceId: event.queued_choice_id ?? null,
    queuedCommandId: event.queued_command_id ?? null,
  };
}

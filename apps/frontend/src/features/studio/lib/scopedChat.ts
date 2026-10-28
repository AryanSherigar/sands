import {
  CARD_TARGET_SLOTS,
  EDITOR_TARGET_SLOTS,
  GUIDE_STEP_TARGET_SLOTS,
  SCOPED_TAB_TEXT_MAX_CHARS,
  TARGET_HOME_LABELS,
} from "../constants/scopedChat";
import type { GuideStepId } from "../constants/guideSteps";
import { GUIDE_TAB_LABEL } from "../constants/studioTabs";
import { OPENING_DOCUMENT_KEY } from "../constants/opening";
import {
  PREMISE_DOCUMENT_KEY,
  WORLD_LORE_DOCUMENT_KEY,
} from "../constants/worldDocumentKeys";
import type {
  ActionTarget,
  AssistantScopedContextPayload,
} from "../types/assistant.types";
import type { EntityResponse } from "../types/entity.types";
import type { LoreDocument } from "../types/lore.types";
import type { ScenarioResponse } from "../types/scenario.types";
import type { GuideView } from "../types/studioTab.types";
import type {
  ScopedChatContext,
  ScopedSlotId,
  ScopedTab,
} from "../types/scopedChat.types";
import type { GroupedCards } from "./cardGroups";
import { renderBlockLine } from "./loreDocument";
import { getAllGuideSteps, getGuideSteps } from "./guideStepsFor";
import { parseTabId } from "./studioTabs";
import { readWorldDocument } from "./worldDocuments";

const SECTION_SEPARATOR = "\n";

export const clampTabText = (text: string): string =>
  text.length > SCOPED_TAB_TEXT_MAX_CHARS ? text.slice(0, SCOPED_TAB_TEXT_MAX_CHARS) : text;

export const resolveScopedTab = (
  activeTabId: string | null,
  guideStep: number,
  guideView: GuideView,
  isAdvanced = false,
): ScopedTab => {
  if (!activeTabId) return { kind: "none" };
  const target = parseTabId(activeTabId);
  if (!target) return { kind: "none" };
  if (target.kind === "guide") {
    const stepId = guideView === "editor" ? null : getGuideSteps(isAdvanced)[guideStep - 1]?.id ?? null;
    return { kind: "guide", stepId };
  }
  if (target.kind === "card" && target.targetId) {
    return { kind: "card", entityId: target.targetId };
  }
  if (target.kind === "feature" && target.targetId) {
    return { kind: "feature", featureId: target.targetId };
  }
  return target.kind === "playtest" ? { kind: "playtest" } : { kind: "none" };
};

export const getSlotForTarget = (
  tab: ScopedTab,
  target: ActionTarget,
): ScopedSlotId | null => {
  if (tab.kind === "card") return CARD_TARGET_SLOTS[target] ?? null;
  if (tab.kind !== "guide") return null;
  if (tab.stepId === null) return EDITOR_TARGET_SLOTS[target] ?? null;
  return GUIDE_STEP_TARGET_SLOTS[tab.stepId as GuideStepId]?.[target] ?? null;
};

export const describeWhereToAccept = (target: ActionTarget): string =>
  TARGET_HOME_LABELS[target] ?? "the tab it belongs to";

const renderDocumentText = (document: LoreDocument): string =>
  document.blocks
    .map(renderBlockLine)
    .filter((line) => line.length > 0)
    .join("\n\n");

const readAlwaysRemember = (scenario: ScenarioResponse): string[] => {
  const stored = scenario.world_data?.alwaysRemember;
  if (!Array.isArray(stored)) return [];
  return stored.filter((line): line is string => typeof line === "string" && line.trim() !== "");
};

const labelled = (label: string, value: string): string =>
  value.trim() ? `${label}: ${value.trim()}` : "";

const joinSections = (sections: string[]): string =>
  sections.filter((section) => section.length > 0).join(SECTION_SEPARATOR);

const namesOf = (entities: EntityResponse[]): string =>
  entities.map((entity) => entity.canonical_name).join(", ");

const buildIdeaText = (scenario: ScenarioResponse): string =>
  joinSections([labelled("Name", scenario.title), labelled("One line idea", scenario.logline ?? "")]);

const buildPremiseText = (scenario: ScenarioResponse): string =>
  joinSections([
    labelled("Genres", scenario.genre_tags.join(", ")),
    labelled("Mood", (scenario.mood_tags ?? []).join(", ")),
    labelled("Premise", renderDocumentText(readWorldDocument(scenario.world_data, PREMISE_DOCUMENT_KEY))),
  ]);

const buildWorldText = (scenario: ScenarioResponse, cards: GroupedCards): string =>
  joinSections([
    labelled("World", renderDocumentText(readWorldDocument(scenario.world_data, WORLD_LORE_DOCUMENT_KEY))),
    labelled("Always remember", readAlwaysRemember(scenario).join(" | ")),
    labelled("Places", namesOf(cards.places)),
    labelled("Groups", namesOf(cards.groups)),
    labelled("Things", namesOf(cards.things)),
  ]);

const buildOpeningText = (scenario: ScenarioResponse): string =>
  joinSections([
    labelled("Opening", renderDocumentText(readWorldDocument(scenario.world_data, OPENING_DOCUMENT_KEY))),
    labelled("Storytelling style", renderDocumentText(scenario.narrator_persona_document ?? { blocks: [] })),
  ]);

const buildPlayerText = (scenario: ScenarioResponse, cards: GroupedCards): string =>
  joinSections([
    labelled("Player", scenario.player_mode === "player_created" ? "The player creates their own character" : "Written by you"),
    labelled("About the player", renderDocumentText(cards.player?.lore_document ?? { blocks: [] })),
  ]);

const buildStepText = (
  stepId: GuideStepId,
  scenario: ScenarioResponse,
  cards: GroupedCards,
): string => {
  switch (stepId) {
    case "idea":
    case "finish":
      return buildIdeaText(scenario);
    case "premise":
      return buildPremiseText(scenario);
    case "player":
      return buildPlayerText(scenario, cards);
    case "characters":
      return labelled("Characters", namesOf(cards.characters));
    case "world":
      return buildWorldText(scenario, cards);
    case "opening":
      return buildOpeningText(scenario);
    case "endings":
    case "tracked_values":
    case "rules":
    case "hard_limits":
    case "extras":
      return "";
  }
};

export const buildGuideTabText = (
  stepId: string | null,
  scenario: ScenarioResponse | null,
  cards: GroupedCards,
): string => {
  if (!scenario) return "";
  if (stepId !== null) return buildStepText(stepId as GuideStepId, scenario, cards);
  return joinSections(
    getAllGuideSteps().map((step) => buildStepText(step.id, scenario, cards)),
  );
};

export const buildCardTabText = (entity: EntityResponse | null): string => {
  if (!entity) return "";
  const lore = renderDocumentText(entity.lore_document ?? { blocks: [] });
  return joinSections([
    labelled("Name", entity.canonical_name),
    labelled("Type", entity.entity_type),
    labelled("Triggers", entity.aliases.join(", ")),
    lore || labelled("About", entity.description ?? ""),
  ]);
};

export const buildScopedTabLabel = (tab: ScopedTab, baseLabel: string): string => {
  if (tab.kind !== "guide" || tab.stepId === null) return baseLabel;
  const step = getAllGuideSteps().find((candidate) => candidate.id === tab.stepId);
  return step ? `${GUIDE_TAB_LABEL} · ${step.name}` : baseLabel;
};

export const toScopedRequestContext = (
  context: ScopedChatContext,
): AssistantScopedContextPayload => ({
  one_line_idea: context.oneLineIdea,
  tab_kind: context.tabKind,
  tab_label: context.tabLabel,
  tab_text: clampTabText(context.tabText),
});

export const EMPTY_SCOPED_CONTEXT: ScopedChatContext = {
  oneLineIdea: "",
  tabKind: "none",
  tabLabel: "",
  tabText: "",
};

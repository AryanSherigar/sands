import {
  JUDGMENT_CHARGE_FACT_LABEL,
  JUDGMENT_FALLBACK_CHARGE,
} from "../constants/judgment.constants";
import type {
  JudgmentCourtMember,
  JudgmentSubjectKind,
  StrategyJudgmentPackage,
} from "../types/judgmentScene.types";
import type { SceneParticipant, SceneViewResponse } from "../types/scene.types";

const PRONOUNCEMENT_RESERVE = 1;
const GOVERNOR_KIND = "governor";

const toCourtMember = (participant: SceneParticipant): JudgmentCourtMember => ({
  participantId: participant.participant_id,
  name: participant.name,
  kind: participant.kind,
  stance: participant.stance ?? null,
});

const readCharge = (view: SceneViewResponse): string =>
  view.situation.facts.find((fact) => fact.label === JUDGMENT_CHARGE_FACT_LABEL)?.value ??
  JUDGMENT_FALLBACK_CHARGE;

const subjectKindOf = (accused: JudgmentCourtMember): JudgmentSubjectKind =>
  accused.kind === GOVERNOR_KIND ? "governor" : "captive";

export const buildJudgmentPackage = (
  view: SceneViewResponse,
  openingFallback = "",
): StrategyJudgmentPackage => {
  const [accusedParticipant, ...advisorParticipants] = view.participants;
  const accused = toCourtMember(accusedParticipant);
  const [opening, ...spoken] = view.transcript;
  return {
    sceneId: view.scene_id,
    turn: view.turn,
    summary: view.situation.summary,
    charge: readCharge(view),
    subjectKind: subjectKindOf(accused),
    accused,
    advisors: advisorParticipants.map(toCourtMember),
    openingText: opening?.leader_text ?? openingFallback,
    exchanges: spoken.map((exchange) => ({
      sequence: exchange.sequence,
      playerText: exchange.player_text,
      courtText: exchange.leader_text,
    })),
    spokenExchangesRemaining: Math.max(0, view.exchanges_remaining - PRONOUNCEMENT_RESERVE),
    outcomeSummary: view.outcome_summary ?? [],
    isResolved: view.status === "resolved" || view.status === "defaulted",
  };
};

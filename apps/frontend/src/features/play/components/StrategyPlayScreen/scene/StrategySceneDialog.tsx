import { parseTableRegions } from "../../../lib/tableRegions";
import React, { useState } from "react";
import {
  AI_INITIATOR,
  NEGOTIATION_SCENE_TYPE,
  REVOLT_TALK_SCENE_TYPE,
} from "../../../constants/scene.constants";
import { useSceneDialog } from "../../../hooks/useSceneDialog";
import { useSimulationWorld } from "../../../hooks/useSimulationWorld";
import type { SceneOutcome, SceneViewResponse } from "../../../types/scene.types";
import { NegotiationConsole } from "./components/NegotiationConsole";
import { NegotiationGrudgesPanel } from "./components/NegotiationGrudgesPanel";
import { NegotiationHeader } from "./components/NegotiationHeader";
import { NegotiationRatificationOverlay } from "./components/NegotiationRatificationOverlay";
import { NegotiationReadingChamber } from "./components/NegotiationReadingChamber";
import { NegotiationRulerDossier } from "./components/NegotiationRulerDossier";
import { NegotiationTreatyDrawer } from "./components/NegotiationTreatyDrawer";
import type { AvatarExpression } from "./components/RulerMeshAvatar.types";
import type { StrategySceneDialogProps } from "./StrategySceneDialog.types";

function getSceneHeaderTitle(sceneType: string, leaderName: string): string {
  if (sceneType === REVOLT_TALK_SCENE_TYPE) return `Talks with ${leaderName}`;
  if (sceneType === "peace") return `Peace Conference with ${leaderName}`;
  return `Peace Talks with ${leaderName}`;
}

const DEFAULT_PREVIEW_SCENE: SceneViewResponse = {
  scene_id: "preview-scene-1",
  scene_type: NEGOTIATION_SCENE_TYPE,
  status: "opened",
  turn: 4,
  is_declinable: true,
  situation: {
    summary:
      "The borderlands of the Valdren Reach stand tense following summer skirmishes. Queen Mira of Dunmere arrives under a flag of truce to negotiate terms of non-aggression.",
    facts: [],
  },
  participants: [
    {
      participant_id: "mira",
      kind: "leader",
      name: "Queen Mira",
      trait_ids: ["cautious", "proud"],
      avatar_url: "/avatars/mira.mavatar",
    },
  ],
  transcript: [
    {
      sequence: 1,
      player_text: "We welcome the Dunmere embassy. Let us speak of peace along the river border.",
      leader_text:
        "Our garrisons watch each other across the Dun with notched arrows. State your terms if you wish the swords sheathed.",
    },
  ],
  exchanges_remaining: 5,
  pending_proposal: {
    proposer_id: "mira",
    counterpart_id: "aldric",
    is_confirmed_by_player: false,
    is_confirmed_by_counterpart: true,
    terms: [
      {
        kind: "non_aggression",
        faction_a: "mira",
        faction_b: "aldric",
        duration_turns: 8,
      },
    ],
  },
  pending_proposal_sequence: 1,
  outcome: null,
};

const DEFAULT_PREVIEW_PEACE_SCENE: SceneViewResponse = {
  scene_id: "preview-peace",
  scene_type: "peace",
  status: "opened",
  turn: 4,
  is_declinable: true,
  situation: {
    summary:
      "War has bled both realms white across the marches. Queen Mira has sent emissaries to discuss an end to hostilities and terms of covenant.",
    facts: [
      { label: "Your war score", value: "18" },
      { label: "Dunmere exhaustion", value: "Moderate" },
    ],
  },
  participants: [
    {
      participant_id: "mira",
      kind: "leader",
      name: "Queen Mira",
      trait_ids: ["cautious", "proud"],
      avatar_url: "/avatars/mira.mavatar",
    },
  ],
  transcript: [
    {
      sequence: 1,
      player_text: "Let the steel be sheathed. What covenant will ensure peace between our houses?",
      leader_text:
        "The border forts are ruined, but our resolve remains unbroken. Here are our terms for an enduring peace.",
    },
  ],
  exchanges_remaining: 4,
  pending_proposal: {
    proposer_id: "mira",
    counterpart_id: "aldric",
    is_confirmed_by_player: false,
    is_confirmed_by_counterpart: true,
    terms: [
      {
        kind: "peace",
        faction_a: "mira",
        faction_b: "aldric",
        tier: "medium",
        guarantor_ids: ["Duchy of Oakhaven"],
      },
      {
        kind: "pay_gold",
        payer_id: "aldric",
        payee_id: "mira",
        amount: 150,
      },
      {
        kind: "cede_region",
        from_faction_id: "mira",
        to_faction_id: "aldric",
        region_id: "reg-highcrag",
      },
    ],
  },
  pending_proposal_sequence: 1,
  outcome: null,
};

export const StrategySceneDialog: React.FC<StrategySceneDialogProps> = ({
  playthroughId,
  sceneId,
  onClose,
}) => {
  const effectivePlaythroughId = playthroughId ?? "preview-playthrough";
  const {
    scene: hookScene,
    isFinished: hookIsFinished,
    isBusy: hookIsBusy,
    stream,
    decision,
  } = useSceneDialog(effectivePlaythroughId, sceneId);

  const { data: world } = useSimulationWorld(playthroughId);
  const [isTableDrawerOpen, setIsTableDrawerOpen] = useState(false);

  const isPeacePreview = sceneId.includes("peace");
  const isUnsupportedPreview = sceneId.includes("unsupported");
  const nonPeacePreviewScene = isUnsupportedPreview
    ? { ...DEFAULT_PREVIEW_SCENE, scene_id: sceneId, scene_type: "unsupported_unknown" }
    : DEFAULT_PREVIEW_SCENE;
  const basePreviewScene = isPeacePreview ? DEFAULT_PREVIEW_PEACE_SCENE : nonPeacePreviewScene;

  const [previewState, setPreviewState] = useState<{
    transcript: typeof DEFAULT_PREVIEW_SCENE.transcript;
    exchangesRemaining: number;
    isFinished: boolean;
    outcome: SceneOutcome | null;
  }>({
    transcript: basePreviewScene.transcript,
    exchangesRemaining: basePreviewScene.exchanges_remaining,
    isFinished: false,
    outcome: null,
  });

  const isPreview = !hookScene && sceneId.startsWith("preview");

  const handlePreviewSend = (text: string) => {
    setPreviewState((prev) => ({
      ...prev,
      transcript: [
        ...prev.transcript,
        {
          sequence: prev.transcript.length + 1,
          player_text: text,
          leader_text:
            "We hear your words. Let us see if our scribes can bind them into honest covenants.",
        },
      ],
      exchangesRemaining: Math.max(0, prev.exchangesRemaining - 1),
    }));
  };

  const handlePreviewDecide = (input: { isConfirmed: boolean }) => {
    setPreviewState((prev) => ({
      ...prev,
      isFinished: true,
      outcome: {
        kind: "terms_card",
        result: input.isConfirmed ? "agreed" : "refused",
      },
    }));
  };

  const scene = isPreview
    ? {
        ...basePreviewScene,
        transcript: previewState.transcript,
        exchanges_remaining: previewState.exchangesRemaining,
        outcome: previewState.outcome,
        status: previewState.isFinished ? ("resolved" as const) : ("opened" as const),
      }
    : hookScene;

  const isSupportedScene =
    scene &&
    (scene.scene_type === NEGOTIATION_SCENE_TYPE ||
      scene.scene_type === "peace" ||
      scene.scene_type === REVOLT_TALK_SCENE_TYPE);

  if (!isSupportedScene) {
    if (world?.status === "awaiting_scene" || isPreview) {
      return (
        <div
          role="alertdialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
        >
          <div className="w-full max-w-md bg-[#F7F0DC] rounded-xl border border-[#3A3128]/30 shadow-2xl p-6 flex flex-col gap-4">
            <div className="flex items-center gap-2 text-[#7A2E1D] font-serif text-lg font-bold">
              <span className="material-symbols-outlined text-[24px]">crisis_alert</span>
              <span>Conference Unavailable</span>
            </div>
            <p className="text-xs text-[#42474B] leading-relaxed">
              The realm is paused for a conference of type &ldquo;{scene?.scene_type ?? "unknown"}&rdquo; (id: {sceneId}) which cannot be conducted. You may order your emissaries to break talks and resume campaign governance under default standing.
            </p>
            <div className="flex justify-end gap-2 pt-2 border-t border-[#3A3128]/15">
              <button
                type="button"
                disabled={decision.isDeciding}
                onClick={() => {
                  if (isPreview) {
                    onClose();
                  } else {
                    decision.decide({ isConfirmed: false });
                  }
                }}
                className="px-4 py-2 bg-[#7A2E1D] hover:bg-[#632416] text-white text-xs font-bold rounded-lg shadow cursor-pointer transition-colors"
              >
                Break Talks &amp; Resume Campaign
              </button>
            </div>
          </div>
        </div>
      );
    }
    return null;
  }

  const isFinished = isPreview ? previewState.isFinished : hookIsFinished;
  const isBusy = isPreview ? false : hookIsBusy;
  const sendMessage = isPreview ? handlePreviewSend : stream.sendMessage;
  const decide = isPreview ? handlePreviewDecide : decision.decide;

  const counterpartParticipant =
    scene.participants?.find((p) => p.kind === "leader") ?? scene.participants?.[0];
  const leaderName = counterpartParticipant?.name ?? "The ruler";

  const matchingRival = world?.rivals?.find(
    (r) =>
      r.faction_id === counterpartParticipant?.participant_id ||
      r.name.toLowerCase() === counterpartParticipant?.name.toLowerCase() ||
      r.leader_name?.toLowerCase() === counterpartParticipant?.name.toLowerCase(),
  );

  const factionName =
    matchingRival?.name ??
    (leaderName === "Queen Mira" ? "Dunmere" : (counterpartParticipant?.name ?? "Valdren"));
  const isAtWar = matchingRival?.relation === "at_war";
  const counterpartPortraitUrl = counterpartParticipant?.avatar_url ?? matchingRival?.avatar_url ?? undefined;
  const counterpartAvatarUrl =
    counterpartParticipant?.avatar_url ??
    matchingRival?.avatar_url ??
    (leaderName === "Queen Mira" ? "/avatars/mira.mavatar" : undefined);

  const isSpeaking = Boolean(hookIsBusy || stream?.isStreaming);

  const outcomeResult =
    scene.outcome?.kind === "terms_card"
      ? scene.outcome.result
      : (scene.outcome as { result?: string } | null | undefined)?.result;

  const isOutcomeRejected =
    outcomeResult === "refused" ||
    outcomeResult === "walked_out" ||
    outcomeResult === "rejected" ||
    outcomeResult === "hostile";

  const isOutcomeConfirmed =
    outcomeResult === "agreed" ||
    outcomeResult === "confirmed" ||
    outcomeResult === "ratified";

  const traits = counterpartParticipant?.trait_ids ?? [];

  let expression: AvatarExpression = "neutral";
  if (isOutcomeRejected) {
    expression = "angry";
  } else if (isOutcomeConfirmed) {
    expression = "smile";
  } else if (traits.includes("cautious")) {
    expression = "halfLidded";
  }

  const playerLeaderName = world?.ruler?.name ?? "King Alden IV";
  const playerFactionName =
    (world?.my_faction as unknown as { name?: string })?.name ?? "Valenreach";
  const playerGold = world?.my_faction?.treasury ?? 340;
  const playerLevies =
    (world?.my_faction as unknown as { total_levies?: number })?.total_levies ??
    world?.my_faction?.manpower ??
    14200;
  const playerPortraitUrl = world?.ruler?.portrait_url ?? undefined;

  const errorMessage = stream.failureMessage ?? decision.errorMessage;
  const handleBreakTalks = (): void => {
    decide({ isConfirmed: false });
  };
  const handleSign = (): void => {
    decide({
      isConfirmed: true,
      proposalSequence: scene.pending_proposal_sequence ?? undefined,
    });
  };

  const isDeclinable = scene.is_declinable !== false;
  const isOffer = scene.initiator === AI_INITIATOR;
  const isRevoltTalk = scene.scene_type === REVOLT_TALK_SCENE_TYPE;
  const headerTitle = getSceneHeaderTitle(scene.scene_type, leaderName);

  return (
    <div
      className="fixed inset-0 z-50 flex flex-col bg-app-bg text-on-surface select-none overflow-hidden"
      role="dialog"
      aria-modal="true"
      aria-label={headerTitle}
    >
      <NegotiationHeader
        title={headerTitle}
        exchangesRemaining={scene.exchanges_remaining}
        isFinished={isFinished}
        onExit={onClose}
      />

      <div className="flex-1 flex min-h-0 relative">
        <NegotiationRulerDossier
          leaderName={leaderName}
          factionName={factionName}
          portraitUrl={counterpartPortraitUrl}
          avatarUrl={counterpartAvatarUrl}
          expression={expression}
          isSpeaking={isSpeaking}
          traitIds={counterpartParticipant?.trait_ids}
          isAtWar={isAtWar}
          playerLeaderName={playerLeaderName}
          playerFactionName={playerFactionName}
          playerPortraitUrl={playerPortraitUrl}
          playerGold={playerGold}
          playerLevies={playerLevies}
        />

        <section className="flex-1 flex flex-col min-w-0 relative h-full overflow-hidden">
          {isOffer && <span className="sr-only">Incoming offer</span>}
          <NegotiationGrudgesPanel
            grudges={scene.voiced_grudges ?? []}
            leaderName={leaderName}
          />
          <NegotiationReadingChamber
            situation={scene.situation.summary}
            transcript={scene.transcript}
            leaderName={leaderName}
            pendingPlayerText={stream.pendingPlayerText}
            streamingReply={stream.reply}
            isStreaming={stream.isStreaming}
            warningMessage={errorMessage}
          />
          <NegotiationConsole
            regions={parseTableRegions(scene.situation.facts)}
            isDisabled={isBusy || isFinished}
            hasPendingProposal={Boolean(scene.pending_proposal)}
            isDrawerOpen={isTableDrawerOpen}
            isDeclinable={isDeclinable}
            isTreatyAvailable={!isRevoltTalk}
            onSend={sendMessage}
            onToggleDrawer={() => setIsTableDrawerOpen((prev) => !prev)}
            onBreakTalks={handleBreakTalks}
          />
          {isRevoltTalk ? null : (
          <NegotiationTreatyDrawer
            isOpen={isTableDrawerOpen}
            proposal={scene.pending_proposal ?? null}
            currentTurn={scene.turn}
            counterpartName={leaderName}
            isBusy={isBusy || isFinished}
            verdict={scene.transcript.at(-1)?.verdict ?? null}
            clauseBands={scene.transcript.at(-1)?.clause_bands ?? []}
            onClose={() => setIsTableDrawerOpen(false)}
            onSign={handleSign}
            onDecline={isDeclinable ? handleBreakTalks : undefined}
          />
          )}
          {isFinished && (
            <NegotiationRatificationOverlay
              outcome={scene.outcome}
              counterpartName={leaderName}
              onClose={onClose}
            />
          )}
        </section>
      </div>
    </div>
  );
};

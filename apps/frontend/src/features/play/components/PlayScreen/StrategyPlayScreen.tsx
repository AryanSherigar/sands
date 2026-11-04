import { describeEdictEffects } from "../../lib/edictEffects";
import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { usePlayStore } from "../../stores/play.store";
import { useSimulationWorld } from "../../hooks/useSimulationWorld";
import { useSimulationCommands } from "../../hooks/useSimulationCommands";
import { useEndTurn } from "../../hooks/useEndTurn";
import { useOrderPlanner } from "../../hooks/useOrderPlanner";
import { useStrategyMap } from "../../hooks/useStrategyMap";
import { useLiveLetter } from "../../hooks/useLiveLetter";
import { useLiveJudgment } from "../../hooks/useLiveJudgment";
import { useStrategyDiplomacy } from "../../hooks/useStrategyDiplomacy";
import { useStrategySituations } from "../../hooks/useStrategySituations";
import { useStrategyEvent } from "../../hooks/useStrategyEvent";
import { useStrategyPlayStore } from "../../stores/strategyPlay.store";
import { deriveDate } from "../../lib/strategyClock";
import { deriveOrdersBudget } from "../../lib/ordersBudget";
import { buildSituationAnswer } from "../../lib/orderBuilders";
import { buildPendingEventPackage } from "../../lib/pendingEventPackage";
import { deriveTurnReport } from "../../lib/turnReportAdapter";
import { prisonersToCaptives } from "../../lib/prisoner-captives";
import { useStrategyAudio } from "../../hooks/useStrategyAudio";
import { useHistoricalWorld } from "../../hooks/useHistoricalWorld";
import { useRestoredTurnReport } from "../../hooks/useRestoredTurnReport";
import { StrategyHistoryScrubber } from "../StrategyPlayScreen/hud/StrategyHistoryScrubber";
import { useMapFocus } from "../../hooks/useMapFocus";
import { usePendingEventNarratives } from "../../hooks/usePendingEventNarratives";
import type { ReactZoomPanPinchRef } from "react-zoom-pan-pinch";
import type { StrategyUIContext } from "@/shared/types/strategy-audio.types";
import type { StrategyWorldSnapshot } from "../../types/strategyPlay.types";
import { StrategyMapViewport } from "../StrategyPlayScreen/map/StrategyMapViewport";
import { StrategyTopCanopy } from "../StrategyPlayScreen/hud/StrategyTopCanopy";
import { StrategyLeftInspector } from "../StrategyPlayScreen/inspector/StrategyLeftInspector";
import { StrategyTurnReportDrawer } from "../StrategyPlayScreen/turnReport/StrategyTurnReportDrawer";
import { StrategyTurnReportLauncher } from "../StrategyPlayScreen/turnReport/StrategyTurnReportLauncher";
import { StrategyRightDrawer } from "../StrategyPlayScreen/factions/StrategyRightDrawer";
import { StrategySceneDialog } from "../StrategyPlayScreen/scene/StrategySceneDialog";
import { StrategyJudgmentDialog } from "../StrategyPlayScreen/judgment/StrategyJudgmentDialog";
import { StrategySituationsDrawer } from "../StrategyPlayScreen/situations/StrategySituationsDrawer";
import { StrategySituationBanner } from "../StrategyPlayScreen/situations/StrategySituationBanner";
import { StrategyEventDialog } from "../StrategyPlayScreen/events/StrategyEventDialog";
import { StrategyOrdersTray } from "../StrategyPlayScreen/orders/StrategyOrdersTray";
import { StrategyChronicleBook } from "../StrategyChronicleBook/StrategyChronicleBook";
import { StrategyEndingGate } from "../StrategyPlayScreen/ending/StrategyEndingGate";
import { StrategyEndTurnModule } from "../StrategyPlayScreen/orders/StrategyEndTurnModule";
import { StrategyNoticeBanner } from "../StrategyPlayScreen/orders/StrategyNoticeBanner";
import { StrategyArmyGroupBar } from "../StrategyPlayScreen/orders/StrategyArmyGroupBar";
import { DeclareWarForm } from "../StrategyPlayScreen/factions/DeclareWarForm";
import { buildDeclareWarOrder } from "../../lib/orderBuilders";
import { StrategyBattleSpeechGate } from "../StrategyPlayScreen/battleSpeech/StrategyBattleSpeechGate";
import { StrategyBattleDecision } from "../StrategyPlayScreen/orders/StrategyBattleDecision";
import { StrategyWarCouncilScreen } from "../StrategyWarCouncil";
import { StrategyLetterDialog } from "../StrategyPlayScreen/letter/StrategyLetterDialog";
import { useProclamationScene } from "../../hooks/useProclamationScene";
import { useResumePendingBattleSpeech } from "../../hooks/useResumePendingBattleSpeech";
import { StrategyProclamationDraftModal } from "../StrategyPlayScreen/proclamation/StrategyProclamationDraftModal";
import { StrategyProclamationDialog } from "../StrategyPlayScreen/proclamation/StrategyProclamationDialog";
import { DEFAULT_PREVIEW_WORLD } from "../StrategyPlayScreen/defaultPreviewWorld";
import { FALLBACK_STRATEGY_MAP } from "../StrategyPlayScreen/fallbackStrategyMap";
import { EMPTY_STRATEGY_MAP } from "../StrategyPlayScreen/emptyStrategyMap";
import { StrategyMapSkeleton } from "../StrategyPlayScreen/map/StrategyMapSkeleton";
import {
  THREE_CROWNS_MAP,
  THREE_CROWNS_WORLD,
} from "../StrategyPlayScreen/threeCrownsDemo";
import {
  StrategyErrorState,
  StrategyLoadingState,
} from "../StrategyPlayScreen/StrategyScreenStates";
import type { ArmyView, CampaignWorldView } from "../../types/simulation.types";
import type { MapDocument } from "@/shared/types/strategy-map.types";

import type { StrategyEventPackage } from "../../types/eventScene.types";

const TARGETING_NOTICE: Record<"move" | "attack", string> = {
  move: "Select a destination region for the march.",
  attack: "Select a region to attack.",
};
const SCENE_PENDING_NOTICE =
  "An economy decision is pending for this turn. It cannot be resolved from this screen yet.";

const DEFAULT_DEV_EVENT: StrategyEventPackage = {
  sceneId: "scene-harvest-ashford",
  category: "trouble",
  title: "Trouble: The Harvest Fails at Ashford",
  subheading: "Decreed under royal seal • Ashford Bailey Jurisdiction",
  turnText: "Turn 48 • Autumn 1042",
  bodyProse:
    "An unseasonable black frost has scorched the rye before the second reaping across the Ashford Vale. The granaries stand hollow, and tenant farmers gather at the abbey gates demanding grain or blood.",
  causeQuote:
    "Because Lord Harl resents your taxes (opinion −40) and prior turn drought was ignored.",
  character: {
    name: "Lord Harl",
    title: "Castellan of Ashford",
    disposition: "Resentful",
  },
  choices: [
    {
      id: "choice-1",
      label: "Release Emergency Crown Grain Reserves",
      effects: ["Gold −50", "Unrest −4", "Stock −200 bu"],
    },
    {
      id: "choice-2",
      label: "Levy an Emergency Food Tithe on Wealthy Monasteries",
      effects: ["Church Opinion −15", "Relations −25", "Unrest +5"],
    },
    {
      id: "choice-3",
      label: "Dispatch 350 Levies to Enforce Order at Ashford",
      effects: ["Spends 1 Order", "Unrest −8", "Fear +10"],
      isMapOrder: true,
    },
  ],
};

function useStrategySelection(mapDoc: MapDocument, armies?: ArmyView[]) {
  const selectedEntity = useStrategyPlayStore((s) => s.selectedEntity);
  const selectedRegion = useMemo(() => {
    if (selectedEntity?.type !== "region") return null;
    return mapDoc.regions.find((r) => r.id === selectedEntity.id) ?? null;
  }, [selectedEntity, mapDoc.regions]);

  const selectedArmy = useMemo(() => {
    if (selectedEntity?.type !== "army") return null;
    return armies?.find((a) => a.army_id === selectedEntity.id) ?? null;
  }, [selectedEntity, armies]);

  return { selectedEntity, selectedRegion, selectedArmy };
}

function useTurnReportItemCount(): number {
  const latestReport = useStrategyPlayStore((s) => s.latestReport);
  return useMemo(() => {
    if (!latestReport) return 0;
    const battleCount = latestReport.battles?.length ?? 0;
    const economyCount = (latestReport.economyLines?.length ?? 0) > 0 ? 1 : 0;
    const itemCount = latestReport.items?.length ?? 0;
    return battleCount + economyCount + itemCount;
  }, [latestReport]);
}

function pickNotice(
  world: CampaignWorldView,
  targetingAction: "move" | "attack" | undefined,
  orderMessage: string | undefined,
  endTurnMessage: string | undefined,
  diplomacyMessage: string | null,
  hasActiveEvent: boolean = false,
): string | null {
  if (targetingAction) return TARGETING_NOTICE[targetingAction];
  if (hasActiveEvent) return null;
  return orderMessage ?? endTurnMessage ?? diplomacyMessage ?? (world.status === "awaiting_scene" ? SCENE_PENDING_NOTICE : null);
}

export function StrategyPlayScreen() {
  const { id: playthroughId } = useParams<{ id: string }>();
  const [mapControls, setMapControls] = useState<ReactZoomPanPinchRef | null>(null);
  const [isTenRegionDemo, setIsTenRegionDemo] = useState(() => {
    // NOTE: demo fixtures are for the preview route only; a real playthrough never reads them.
    if (typeof window === "undefined" || playthroughId) return false;
    const search = new URLSearchParams(window.location.search);
    const demo = search.get("demo");
    const scenario = search.get("scenario");
    return (
      demo === "10-region" ||
      demo === "three-crowns" ||
      scenario === "three-crowns-expanded"
    );
  });

  const fallbackMap = isTenRegionDemo ? THREE_CROWNS_MAP : FALLBACK_STRATEGY_MAP;
  const fallbackWorld = isTenRegionDemo ? THREE_CROWNS_WORLD : DEFAULT_PREVIEW_WORLD;

  const isPlaythrough = Boolean(playthroughId);
  const scenarioId = usePlayStore((s) => s.playthrough?.scenario_id);
  const { data: mapData, isLoading: isMapLoading } = useStrategyMap(scenarioId);
  const { data: world, isLoading, isError, refetch } = useSimulationWorld(playthroughId);
  const { cancelMutation } = useSimulationCommands(playthroughId);
  const [isLegacyRequested, setIsLegacyRequested] = useState(false);

  const activeMapDoc = isPlaythrough
    ? (mapData ?? EMPTY_STRATEGY_MAP)
    : (mapData ?? (scenarioId ? EMPTY_STRATEGY_MAP : fallbackMap));
  const liveWorld = world ?? fallbackWorld;
  const historyTurn = useStrategyPlayStore((s) => s.historyTurn);
  const pendingWarTargetId = useStrategyPlayStore((s) => s.pendingWarTargetId);
  const setPendingWarTarget = useStrategyPlayStore((s) => s.setPendingWarTarget);
  const setHistoryTurn = useStrategyPlayStore((s) => s.setHistoryTurn);
  const history = useHistoricalWorld(playthroughId, historyTurn);
  const activeWorld = history.data ?? liveWorld;
  const latestCompletedTurn = Math.max(0, liveWorld.turn - 1);
  const regionNames = useMemo(
    () => Object.fromEntries(activeMapDoc.regions.map((region) => [region.id, region.name])),
    [activeMapDoc.regions],
  );
  const factionNames = useMemo(
    () => Object.fromEntries(activeWorld.rivals.map((rival) => [rival.faction_id, rival.name])),
    [activeWorld.rivals],
  );

  useRestoredTurnReport(playthroughId, liveWorld, regionNames);
  const { endTurn, isEndingTurn, errorInfo } = useEndTurn(playthroughId, regionNames);
  const { selectedEntity, selectedRegion, selectedArmy } = useStrategySelection(
    activeMapDoc,
    activeWorld.armies,
  );
  const planner = useOrderPlanner(playthroughId, activeWorld);
  const negotiation = useStrategyDiplomacy(playthroughId, activeWorld);
  const { situations, activeCrisesCount, escalatedSituation } = useStrategySituations(
    activeWorld,
    regionNames,
  );
  const { eventPackage, resolveChoice } = useStrategyEvent(playthroughId, activeWorld);
  const letter = useLiveLetter(playthroughId, activeWorld);
  const judgment = useLiveJudgment(playthroughId, activeWorld);
  const proclamation = useProclamationScene(playthroughId);
  const edictSource = activeWorld.active_proclamation ?? proclamation.activeEdict;
  const activeEdict = edictSource
    ? {
        title: edictSource.legal_summary,
        remainingTurns: edictSource.remaining_turns,
        effects: describeEdictEffects(edictSource.ongoing_modifiers),
      }
    : null;
  const [devEventPackage, setDevEventPackage] = useState<StrategyEventPackage | null>(null);
  const [reviewedEventId, setReviewedEventId] = useState<string | null>(null);
  const reviewedPackage = useMemo(
    () => buildPendingEventPackage(activeWorld, reviewedEventId, regionNames),
    [activeWorld, reviewedEventId, regionNames],
  );
  const [isBannerDismissed, setIsBannerDismissed] = useState(false);
  const [activeWarCouncilBattleId, setActiveWarCouncilBattleId] = useState<string | null>(null);
  useResumePendingBattleSpeech(
    playthroughId,
    historyTurn === null ? activeWorld.battles : undefined,
    activeWarCouncilBattleId,
    setActiveWarCouncilBattleId,
  );
  const closeScene = useStrategyPlayStore((s) => s.closeScene);

  useEffect(() => {
    if (!import.meta.env.DEV) return;
    (window as unknown as { __TRIGGER_EVENT__: (pkg?: StrategyEventPackage) => void }).__TRIGGER_EVENT__ = (pkg) => {
      setDevEventPackage(pkg ?? DEFAULT_DEV_EVENT);
    };
  }, []);

  useEffect(() => {
    if (!import.meta.env.DEV) return;
    (
      window as unknown as {
        __TRIGGER_NEGOTIATION__: (sceneId?: string) => void;
      }
    ).__TRIGGER_NEGOTIATION__ = (id) => {
      useStrategyPlayStore.getState().openScene(id ?? "preview-scene-1");
    };
  }, []);

  const activeEventPackage = eventPackage ?? reviewedPackage ?? devEventPackage;

  const selectEntity = useStrategyPlayStore((s) => s.selectEntity);
  const groupArmyIds = useStrategyPlayStore((s) => s.groupArmyIds);
  const toggleGroupArmy = useStrategyPlayStore((s) => s.toggleGroupArmy);
  const clearGroupArmies = useStrategyPlayStore((s) => s.clearGroupArmies);
  const activeMapMode = useStrategyPlayStore((s) => s.activeMapMode);
  const setActiveMapMode = useStrategyPlayStore((s) => s.setActiveMapMode);
  const activeRightTab = useStrategyPlayStore((s) => s.activeRightTab);
  const setActiveRightTab = useStrategyPlayStore((s) => s.setActiveRightTab);
  const isRightDrawerPinned = useStrategyPlayStore((s) => s.isRightDrawerPinned);
  const togglePinRightDrawer = useStrategyPlayStore((s) => s.togglePinRightDrawer);
  const orderFeedback = useStrategyPlayStore((s) => s.orderFeedback);
  const setOrderFeedback = useStrategyPlayStore((s) => s.setOrderFeedback);
  const focusMapLocation = useStrategyPlayStore((s) => s.focusMapLocation);
  const isSituationsOpen = useStrategyPlayStore((s) => s.isSituationsOpen);
  const activeSituationId = useStrategyPlayStore((s) => s.activeSituationId);
  const openSituations = useStrategyPlayStore((s) => s.openSituations);
  const closeSituations = useStrategyPlayStore((s) => s.closeSituations);
  const toggleSituations = useStrategyPlayStore((s) => s.toggleSituations);
  const isTurnReportOpen = useStrategyPlayStore((s) => s.isTurnReportOpen);
  const turnReportItemCount = useTurnReportItemCount();

  const activeContext: StrategyUIContext = useMemo(() => {
    if (letter.pkg && letter.isOpen) return "letter";
    if (negotiation.sceneId && letter.isSceneTypeResolved && !letter.isLetterScene) return "negotiation";
    if (activeEventPackage) return "event";
    if (activeWorld?.status === "awaiting_battle_decision") return "war_council";
    if (isTurnReportOpen) return "turn_report";
    return "map";
  }, [
    letter.pkg,
    letter.isOpen,
    negotiation.sceneId,
    letter.isSceneTypeResolved,
    letter.isLetterScene,
    activeEventPackage,
    activeWorld?.status,
    isTurnReportOpen,
  ]);

  useStrategyAudio({
    worldState: activeWorld as unknown as StrategyWorldSnapshot,
    uiContext: activeContext,
    seed: playthroughId,
  });

  useMapFocus(activeMapDoc, mapControls);
  usePendingEventNarratives(playthroughId, activeWorld.pending_events);

  useEffect(() => () => useStrategyPlayStore.getState().reset(), []);

  useEffect(() => {
    if (!playthroughId && !useStrategyPlayStore.getState().latestReport) {
      const initialReport = deriveTurnReport(null, activeWorld, regionNames);
      useStrategyPlayStore.getState().setLatestReport(initialReport);
      useStrategyPlayStore.setState({ hasUnreadTurnReport: true });
    }
  }, [playthroughId, activeWorld, regionNames]);

  if (isLoading) return <StrategyLoadingState />;
  if (isError) return <StrategyErrorState onRetry={() => void refetch()} />;

  const handleSelectEntity: typeof selectEntity = (entity) => {
    if (planner.targeting && entity?.type === "region") {
      planner.handleRegionTargeted(entity.id);
      return;
    }
    selectEntity(entity);
  };
  const handleOpenTreasury = (): void => {
    const currentTab = useStrategyPlayStore.getState().activeRightTab;
    setActiveRightTab(currentTab === "treasury" ? null : "treasury");
  };
  const budget = deriveOrdersBudget(activeWorld);
  const nextDate = deriveDate(activeWorld.clock, 1);
  const reignStart = deriveDate(activeWorld.clock, -activeWorld.clock.turn);
  const reignEnd = deriveDate(activeWorld.clock);
  const eraLabel = `${reignStart.season} ${reignStart.year} to ${reignEnd.season} ${reignEnd.year}`;
  const notice = pickNotice(
    activeWorld,
    planner.targeting?.action,
    orderFeedback?.message,
    errorInfo?.message,
    negotiation.errorMessage,
    Boolean(eventPackage),
  );

  return (
    <main className="strategy-surface relative w-screen h-screen overflow-hidden bg-[#EFE4C8] select-none">
      {isPlaythrough && isMapLoading ? (
        <StrategyMapSkeleton />
      ) : (
        <StrategyMapViewport
          document={activeMapDoc}
          world={activeWorld}
          selectedEntity={selectedEntity}
          onSelectEntity={handleSelectEntity}
          situations={situations}
          activeMapMode={activeMapMode}
          onControlsReady={setMapControls}
          groupArmyIds={groupArmyIds}
          onToggleGroupArmy={toggleGroupArmy}
          onSelectSituation={(sitId, regId) => {
            openSituations(sitId);
            focusMapLocation(regId);
            selectEntity({ type: "region", id: regId });
          }}
        />
      )}
      {!playthroughId && (
        <aside
          aria-label="Demo scenario picker"
          className="fixed bottom-0 left-1/2 -translate-x-1/2 z-50 hidden items-center gap-1.5 px-3 py-0.5 sm:flex bg-[#F5EEDC]/95 border border-[#D5C29D] rounded-t-md shadow-md text-xs font-serif pointer-events-auto"
        >
          <span className="text-[#6B5E4F] font-semibold">Demo Scenario:</span>
          <button
            type="button"
            onClick={() => setIsTenRegionDemo((prev) => !prev)}
            className="font-bold text-[#2A231C] underline decoration-[#9D8461] hover:text-[#7A2E1D]"
          >
            {isTenRegionDemo ? "10 Regions (Three Crowns Expanded)" : "4 Regions (Dunmere Vale)"}
          </button>
        </aside>
      )}
      <StrategyArmyGroupBar
        count={groupArmyIds.length}
        isTargeting={Boolean(planner.targeting)}
        onMove={() => planner.handleGroupAction("move")}
        onHalt={() => planner.handleGroupAction("halt")}
        onMerge={() => planner.handleGroupAction("merge")}
        onClear={clearGroupArmies}
      />
      <StrategyTopCanopy
        world={activeWorld}
        activeMapMode={activeMapMode}
        onSelectMapMode={setActiveMapMode}
        activeCrisesCount={activeCrisesCount}
        onToggleSituations={toggleSituations}
        letterDispatchNumber={letter.dispatchNumber}
        onOpenLetter={letter.handleOpen}
        onOpenTreasury={handleOpenTreasury}
        playthroughId={playthroughId}
        isHistoryAvailable={Boolean(playthroughId) && latestCompletedTurn > 0}
        isHistoryActive={historyTurn !== null}
        onToggleHistory={() => setHistoryTurn(historyTurn === null ? latestCompletedTurn : null)}
        activeEdict={activeEdict}
        onIssueProclamation={proclamation.openDraft}
      />
      {historyTurn !== null ? (
        <StrategyHistoryScrubber
          latestTurn={latestCompletedTurn}
          viewedTurn={historyTurn}
          isLoading={history.isFetching}
          hasFailed={history.isError}
          onChangeTurn={setHistoryTurn}
          onReturnToPresent={() => setHistoryTurn(null)}
        />
      ) : null}
      <StrategyLeftInspector
        selectedEntity={selectedEntity}
        region={selectedRegion}
        army={selectedArmy}
        world={activeWorld}
        onClose={() => selectEntity(null)}
        onAction={planner.handleInspectorAction}
      />
      <StrategyTurnReportDrawer />
      <StrategyRightDrawer
        playthroughId={playthroughId}
        rivals={activeWorld.rivals}
        diplomacy={negotiation.diplomacy}
        activeTab={activeRightTab}
        isPinned={isRightDrawerPinned}
        world={activeWorld}
        onSubmitOrder={planner.submitOrder}
        regionNames={regionNames}
        onSelectTab={setActiveRightTab}
        onTogglePin={togglePinRightDrawer}
        onJumpToRegion={focusMapLocation}
      />
      {negotiation.sceneId &&
      letter.isSceneTypeResolved &&
      !letter.isLetterScene &&
      judgment.isSceneTypeResolved &&
      !judgment.isJudgmentScene ? (
        <StrategySceneDialog
          playthroughId={playthroughId}
          sceneId={negotiation.sceneId}
          onClose={closeScene}
        />
      ) : null}
      <StrategySituationsDrawer
        isOpen={isSituationsOpen}
        situations={situations}
        activeSituationId={activeSituationId}
        onClose={closeSituations}
        onCenterMap={(regionId) => {
          focusMapLocation(regionId);
          selectEntity({ type: "region", id: regionId });
        }}
        ordersRemaining={activeWorld.orders_remaining}
        onExecuteLever={(lever) =>
          void planner.submitOrder(
            buildSituationAnswer(
              activeWorld.my_faction.id,
              lever.source,
              lever.eventId,
              lever.choiceId,
            ),
          )
        }
        onCancelLever={(commandId) => cancelMutation.mutate(commandId)}
        onReviewEvent={setReviewedEventId}
      />
      {escalatedSituation && !isBannerDismissed && (
        <StrategySituationBanner
          situation={escalatedSituation}
          onCenterMap={(regionId) => {
            focusMapLocation(regionId);
            selectEntity({ type: "region", id: regionId });
          }}
          onReviewEvent={setReviewedEventId}
          onDismiss={() => setIsBannerDismissed(true)}
        />
      )}
      {activeEventPackage && (
        <StrategyEventDialog
          isOpen={Boolean(activeEventPackage)}
          playthroughId={playthroughId}
          eventPackage={activeEventPackage}
          onSelectOption={(optionId) => {
            if (eventPackage) void resolveChoice(optionId);
            else if (reviewedPackage?.eventId) {
              void planner.submitOrder(
                buildSituationAnswer(
                  activeWorld.my_faction.id,
                  reviewedPackage.source,
                  reviewedPackage.eventId,
                  optionId,
                ),
              );
            }
            setDevEventPackage(null);
            setReviewedEventId(null);
          }}
          onCancelQueued={(commandId) => cancelMutation.mutate(commandId)}
          onClose={() => {
            setDevEventPackage(null);
            setReviewedEventId(null);
          }}
        />
      )}
      {judgment.pkg && (
        <StrategyJudgmentDialog
          isOpen={judgment.isOpen}
          pkg={judgment.pkg}
          liveText={judgment.liveText}
          isStreaming={judgment.isStreaming}
          failureMessage={judgment.failureMessage}
          canRetryOpen={judgment.canRetryOpen}
          onRetryOpen={judgment.handleRetryOpen}
          onSpeak={judgment.handleSpeak}
          onPronounce={judgment.handlePronounce}
          onDismissReveal={judgment.handleDismissReveal}
          onClose={judgment.handleClose}
        />
      )}
      {letter.pkg && (
        <StrategyLetterDialog
          isOpen={letter.isOpen}
          pkg={letter.pkg}
          onSeal={letter.handleSeal}
          onClose={letter.handleClose}
          onRequestScribeDraft={letter.requestScribeDraft}
          onDecline={letter.handleDecline}
        />
      )}
      <StrategyProclamationDraftModal
        isOpen={proclamation.isDraftOpen}
        isClassifying={proclamation.isClassifying}
        draftError={proclamation.draftError}
        activeEdict={activeEdict}
        onSubmitDraft={proclamation.submitDraft}
        onClose={proclamation.closeDraft}
      />
      {proclamation.councilPackage && (
        <StrategyProclamationDialog
          isOpen={proclamation.isCouncilOpen}
          ministers={proclamation.councilPackage.ministers}
          legalSummary={proclamation.councilPackage.draft.legal_summary}
          domain={proclamation.councilPackage.draft.domain}
          burden={proclamation.councilPackage.draft.burden}
          transcript={proclamation.transcript}
          isStreaming={proclamation.isStreaming}
          isEnacting={proclamation.isEnacting}
          onAddressCouncil={proclamation.sendAddress}
          onPronounce={(verdict) => {
            void proclamation.commitDecision(
              verdict,
              proclamation.councilPackage?.is_rescinding_previous,
              () => {
                if (playthroughId) {
                  void refetch();
                }
              }
            );
          }}
          onClose={proclamation.closeCouncil}
        />
      )}
      {notice ? (
        <StrategyNoticeBanner
          message={notice}
          onDismiss={planner.targeting ? planner.cancelTargeting : () => setOrderFeedback(null)}
        />
      ) : null}
      <StrategyOrdersTray
        orders={activeWorld.queued_orders}
        ordersRemaining={budget.remaining}
        ordersTotal={budget.total}
        regionNames={regionNames}
        factionNames={factionNames}
        onCancelOrder={(commandId) => cancelMutation.mutate(commandId)}
      />
      <StrategyTurnReportLauncher itemCount={turnReportItemCount} />
      {playthroughId && !activeWorld.ending && activeWorld.status === "awaiting_battle_decision" && (
        <StrategyBattleDecision
          playthroughId={playthroughId}
          world={activeWorld}
          regionNames={regionNames}
          onTakeCommand={(battleId) => setActiveWarCouncilBattleId(battleId)}
        />
      )}
      {activeWorld.status === "awaiting_commands" && !activeWorld.ending && (
        <div className="absolute bottom-28 left-1/2 z-30 -translate-x-1/2 flex items-center gap-3">
          {activeWorld.battles?.some(
            (b) => b.control_mode === "player" && b.status !== "resolved",
          ) && (
            <button
              type="button"
              onClick={() => {
                const b = activeWorld.battles.find(
                  (item) => item.control_mode === "player" && item.status !== "resolved",
                );
                if (b) setActiveWarCouncilBattleId(b.id);
              }}
              className="rounded-md bg-[#46606E] px-5 py-3 text-white shadow-lg hover:bg-[#354F5A] focus-visible:outline focus-visible:outline-2"
            >
              Open War Council
            </button>
          )}
          <button
            type="button"
            disabled={isEndingTurn}
            onClick={() => endTurn()}
            className="rounded-md bg-[#46606E] px-5 py-3 text-white shadow-lg hover:bg-[#354F5A] focus-visible:outline focus-visible:outline-2 disabled:opacity-50"
          >
            {isEndingTurn ? "Resolving battle…" : "Advance battle round"}
          </button>
        </div>
      )}
      {activeWarCouncilBattleId && playthroughId && (
        <StrategyBattleSpeechGate
          playthroughId={playthroughId}
          battleId={activeWarCouncilBattleId}
        >
          <StrategyWarCouncilScreen
            playthroughId={playthroughId}
            battleId={activeWarCouncilBattleId}
            regionNames={regionNames}
            world={activeWorld}
            heldCaptives={prisonersToCaptives(activeWorld.own_prisoners)}
            onReturnToMap={() => setActiveWarCouncilBattleId(null)}
          />
        </StrategyBattleSpeechGate>
      )}
      {pendingWarTargetId ? (
        <DeclareWarForm
          targetName={activeWorld.rivals.find((rival) => rival.faction_id === pendingWarTargetId)?.name ?? pendingWarTargetId}
          grounds={(activeWorld.usable_grounds ?? []).filter((ground) => ground.target_faction_id === pendingWarTargetId)}
          regionNames={regionNames}
          onSubmit={(groundId) => {
            void planner.submitOrder(buildDeclareWarOrder(activeWorld.my_faction.id, pendingWarTargetId, groundId));
            setPendingWarTarget(null);
          }}
          onCancel={() => setPendingWarTarget(null)}
        />
      ) : null}
      <StrategyEndTurnModule
        ordersRemaining={activeWorld.orders_remaining}
        nextSeason={`${nextDate.season} ${nextDate.year}`}
        isLoading={isEndingTurn}
        isDisabled={historyTurn !== null || !playthroughId || Boolean(activeWorld.ending) || activeWorld.status === "awaiting_scene" || activeWorld.status === "awaiting_battle_decision" || activeWorld.status === "awaiting_commands"}
        onEndTurn={() => endTurn()}
      />
      {activeWorld.ending && isLegacyRequested ? (
        <StrategyChronicleBook
          playthroughId={playthroughId}
          rulerName={activeWorld.ruler.name}
          chroniclerId={activeWorld.ruler.chronicler_id}
          eraLabel={eraLabel}
          onClose={() => setIsLegacyRequested(false)}
        />
      ) : null}
      {activeWorld.ending && !isLegacyRequested ? (
        <StrategyEndingGate
          ending={activeWorld.ending}
          scenarioId={scenarioId}
          onReadLegacy={() => setIsLegacyRequested(true)}
        />
      ) : null}
    </main>
  );
}

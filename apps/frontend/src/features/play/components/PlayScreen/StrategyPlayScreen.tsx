import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { usePlayStore } from "../../stores/play.store";
import { useSimulationWorld } from "../../hooks/useSimulationWorld";
import { useSimulationCommands } from "../../hooks/useSimulationCommands";
import { useEndTurn } from "../../hooks/useEndTurn";
import { useOrderPlanner } from "../../hooks/useOrderPlanner";
import { useStrategyMap } from "../../hooks/useStrategyMap";
import { useStrategyDiplomacy } from "../../hooks/useStrategyDiplomacy";
import { useStrategySituations } from "../../hooks/useStrategySituations";
import { useStrategyEvent } from "../../hooks/useStrategyEvent";
import { useStrategyPlayStore } from "../../stores/strategyPlay.store";
import { deriveDate } from "../../lib/strategyClock";
import { deriveOrdersBudget } from "../../lib/ordersBudget";
import { buildSituationAnswer } from "../../lib/orderBuilders";
import { buildPendingEventPackage } from "../../lib/pendingEventPackage";
import { deriveTurnReport } from "../../lib/turnReportAdapter";
import { StrategyMapViewport } from "../StrategyPlayScreen/map/StrategyMapViewport";
import { StrategyTopCanopy } from "../StrategyPlayScreen/hud/StrategyTopCanopy";
import { StrategyLeftInspector } from "../StrategyPlayScreen/inspector/StrategyLeftInspector";
import { StrategyTurnReportDrawer } from "../StrategyPlayScreen/turnReport/StrategyTurnReportDrawer";
import { StrategyTurnReportLauncher } from "../StrategyPlayScreen/turnReport/StrategyTurnReportLauncher";
import { StrategyRightDrawer } from "../StrategyPlayScreen/factions/StrategyRightDrawer";
import { StrategySceneDialog } from "../StrategyPlayScreen/scene/StrategySceneDialog";
import { StrategySituationsDrawer } from "../StrategyPlayScreen/situations/StrategySituationsDrawer";
import { StrategySituationBanner } from "../StrategyPlayScreen/situations/StrategySituationBanner";
import { StrategyEventDialog } from "../StrategyPlayScreen/events/StrategyEventDialog";
import { StrategyOrdersTray } from "../StrategyPlayScreen/orders/StrategyOrdersTray";
import { StrategyEndTurnModule } from "../StrategyPlayScreen/orders/StrategyEndTurnModule";
import { StrategyNoticeBanner } from "../StrategyPlayScreen/orders/StrategyNoticeBanner";
import { StrategyBattleDecision } from "../StrategyPlayScreen/orders/StrategyBattleDecision";
import { DEFAULT_PREVIEW_WORLD } from "../StrategyPlayScreen/defaultPreviewWorld";
import { FALLBACK_STRATEGY_MAP } from "../StrategyPlayScreen/fallbackStrategyMap";
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

function useMapFocusObserver(mapDoc: MapDocument): void {
  const mapFocusTarget = useStrategyPlayStore((s) => s.mapFocusTarget);
  useEffect(() => {
    if (!mapFocusTarget) return;
    const region = mapDoc.regions.find((r) => r.id === mapFocusTarget.regionId);
    if (!region) return;
  }, [mapFocusTarget, mapDoc.regions]);
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
  const scenarioId = usePlayStore((s) => s.playthrough?.scenario_id);
  const { data: mapData } = useStrategyMap(scenarioId);
  const { data: world, isLoading, isError, refetch } = useSimulationWorld(playthroughId);
  const { cancelMutation } = useSimulationCommands(playthroughId);

  const activeMapDoc = mapData ?? FALLBACK_STRATEGY_MAP;
  const activeWorld = world ?? DEFAULT_PREVIEW_WORLD;
  const regionNames = useMemo(
    () => Object.fromEntries(activeMapDoc.regions.map((region) => [region.id, region.name])),
    [activeMapDoc.regions],
  );

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
  const [devEventPackage, setDevEventPackage] = useState<StrategyEventPackage | null>(null);
  const [reviewedEventId, setReviewedEventId] = useState<string | null>(null);
  const reviewedPackage = useMemo(
    () => buildPendingEventPackage(activeWorld, reviewedEventId, regionNames),
    [activeWorld, reviewedEventId, regionNames],
  );
  const [isBannerDismissed, setIsBannerDismissed] = useState(false);
  const closeScene = useStrategyPlayStore((s) => s.closeScene);

  useEffect(() => {
    (window as unknown as { __TRIGGER_EVENT__: (pkg?: StrategyEventPackage) => void }).__TRIGGER_EVENT__ = (pkg) => {
      setDevEventPackage(pkg ?? DEFAULT_DEV_EVENT);
    };
  }, []);

  const activeEventPackage = eventPackage ?? reviewedPackage ?? devEventPackage;

  const selectEntity = useStrategyPlayStore((s) => s.selectEntity);
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
  const turnReportItemCount = useTurnReportItemCount();

  useMapFocusObserver(activeMapDoc);

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
  const budget = deriveOrdersBudget(activeWorld);
  const nextDate = deriveDate(activeWorld.clock, 1);
  const notice = pickNotice(
    activeWorld,
    planner.targeting?.action,
    orderFeedback?.message,
    errorInfo?.message,
    negotiation.errorMessage,
    Boolean(eventPackage),
  );

  return (
    <main className="relative w-screen h-screen overflow-hidden bg-[#EFE4C8] select-none">
      <StrategyMapViewport
        document={activeMapDoc}
        world={activeWorld}
        selectedEntity={selectedEntity}
        onSelectEntity={handleSelectEntity}
        situations={situations}
        onSelectSituation={(sitId, regId) => {
          openSituations(sitId);
          focusMapLocation(regId);
          selectEntity({ type: "region", id: regId });
        }}
      />
      <StrategyTopCanopy
        world={activeWorld}
        activeMapMode={activeMapMode}
        onSelectMapMode={setActiveMapMode}
        activeCrisesCount={activeCrisesCount}
        onToggleSituations={toggleSituations}
      />
      <StrategyLeftInspector
        selectedEntity={selectedEntity}
        region={selectedRegion}
        army={selectedArmy}
        world={activeWorld}
        onClose={() => selectEntity(null)}
        onAction={planner.handleInspectorAction}
      />
      <StrategyTurnReportDrawer onContinue={() => endTurn()} />
      <StrategyRightDrawer
        playthroughId={playthroughId}
        rivals={activeWorld.rivals}
        diplomacy={negotiation.diplomacy}
        activeTab={activeRightTab}
        isPinned={isRightDrawerPinned}
        onSelectTab={setActiveRightTab}
        onTogglePin={togglePinRightDrawer}
        onJumpToRegion={focusMapLocation}
      />
      {playthroughId && negotiation.sceneId ? (
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
        onCancelOrder={(commandId) => cancelMutation.mutate(commandId)}
      />
      <StrategyTurnReportLauncher itemCount={turnReportItemCount} />
      {playthroughId && activeWorld.status === "awaiting_battle_decision" && (
        <StrategyBattleDecision playthroughId={playthroughId} world={activeWorld} regionNames={regionNames} />
      )}
      {activeWorld.status === "awaiting_commands" && (
        <button type="button" disabled={isEndingTurn} onClick={() => endTurn()} className="absolute bottom-28 left-1/2 z-40 -translate-x-1/2 rounded-md bg-[#46606E] px-5 py-3 text-white shadow-lg hover:bg-[#354F5A] focus-visible:outline focus-visible:outline-2 disabled:opacity-50">
          {isEndingTurn ? "Resolving battle…" : "Advance battle round"}
        </button>
      )}
      <StrategyEndTurnModule
        ordersRemaining={activeWorld.orders_remaining}
        nextSeason={`${nextDate.season} ${nextDate.year}`}
        isLoading={isEndingTurn}
        isDisabled={!playthroughId || activeWorld.status === "awaiting_scene" || activeWorld.status === "awaiting_battle_decision" || activeWorld.status === "awaiting_commands"}
        onEndTurn={() => endTurn()}
      />
    </main>
  );
}

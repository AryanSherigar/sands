import { usePlayStore } from "../../stores/play.store";
import { MAX_BATTLE_WAVES } from "../../constants/strategy.constants";
import { buildBattleParticipants } from "../../lib/battleParticipants";
import { formatTerrainLabel, formatWeatherLabel } from "../../lib/battleLabels";
import type { CampaignWorldView } from "../../types/simulation.types";
import type { BattleView, NobleCaptive } from "./StrategyWarCouncil.types";
import { WarCouncilLoadState } from "./WarCouncilLoadState";
import { WarCouncilOverlays } from "./WarCouncilOverlays";
import { useWarCouncilState } from "./hooks/useWarCouncilState";
import { WarCouncilHeader } from "./hud/WarCouncilHeader";
import { WarCouncilRightPillar } from "./pillar/WarCouncilRightPillar";
import { WarCouncilLeftRail } from "./rail/WarCouncilLeftRail";
import { WarCouncilTheater } from "./theater/WarCouncilTheater";

export interface StrategyWarCouncilScreenProps {
  playthroughId: string;
  battleId: string;
  regionNames: Record<string, string>;
  world: Pick<CampaignWorldView, "rivals" | "armies">;
  heldCaptives?: NobleCaptive[];
  onReturnToMap: () => void;
  initialBattle?: BattleView;
}

const sumTroops = (troops: Record<string, number>): number =>
  Object.values(troops).reduce((total, count) => total + count, 0);

export function StrategyWarCouncilScreen({
  playthroughId,
  battleId,
  regionNames,
  world,
  heldCaptives,
  onReturnToMap,
  initialBattle,
}: StrategyWarCouncilScreenProps) {
  const council = useWarCouncilState(playthroughId, battleId, initialBattle);
  const isAudioMuted = usePlayStore((state) => state.is_audio_muted);
  const toggleAudioMute = usePlayStore((state) => state.toggleAudioMute);
  const { battle, odds } = council;

  if (!battle) {
    return (
      <WarCouncilLoadState
        isLoading={council.isLoading}
        errorMessage={council.loadErrorMessage}
        onRetry={() => void council.retryLoad()}
        onReturnToMap={onReturnToMap}
      />
    );
  }

  const regionName = regionNames[battle.region_id] ?? battle.region_id;
  const participants = buildBattleParticipants(battle, world);
  const totalTroops = sumTroops(battle.own_contingent?.troops ?? {});
  const opponentFactionIds = new Set(battle.opponents.map((opponent) => opponent.faction_id));
  const battleCaptives = heldCaptives?.filter((captive) => opponentFactionIds.has(captive.factionId));
  const morale = battle.own_contingent?.morale ?? null;

  const handleConfirmRetreat = async () => {
    const didWithdraw = await council.confirmRetreat();
    if (didWithdraw) onReturnToMap();
  };

  return (
    <main className="strategy-surface fixed inset-0 z-50 w-full h-screen bg-[#EFE4C8] text-[#221a12] font-sans flex flex-col overflow-hidden">
      <WarCouncilHeader
        regionName={regionName}
        battleTitle={`Battle of ${regionName}`}
        turnText={`Turn ${battle.current_turn} • Wave ${battle.exchanges_used} of ${MAX_BATTLE_WAVES}`}
        terrainName={formatTerrainLabel(battle.terrain)}
        weatherName={formatWeatherLabel(battle.weather)}
        mandatesText={`${battle.command_cost} command ${battle.command_cost === 1 ? "point" : "points"} per order`}
        frontageText={battle.frontage ? `Frontage: ${battle.frontage.toLocaleString()} abreast` : undefined}
        isRetreatDisabled={!council.canWithdraw}
        isMuted={isAudioMuted}
        onToggleAudio={toggleAudioMute}
        onOpenCodex={council.toggleCodex}
        onOpenRetreat={council.toggleRetreatModal}
        onReturnToMap={onReturnToMap}
      />

      <div className="flex-1 flex flex-col lg:flex-row w-full overflow-y-auto lg:overflow-hidden relative pb-40 lg:pb-0">
        <WarCouncilLeftRail
          playerCommander={participants.playerCommander}
          enemyCommander={participants.enemyCommander}
          odds={odds}
          playerFactionName={participants.playerFactionName}
          enemyFactionName={participants.enemyFactionName}
          reports={council.reports}
          activeDoctrineName={council.stagedPlan.tactic}
        />

        <WarCouncilTheater
          opponent={battle.opponents[0]!}
          formation={council.stagedPlan.formation}
          anchorSlot={council.activeAnchor}
          onSelectSlot={council.setAnchor}
          wards={council.wards}
          onUpdateCohortCount={council.updateCohortCount}
          onReorderRank={council.reorderRank}
          onSelectAnchor={council.setAnchor}
          troops={battle.own_contingent?.troops ?? {}}
          activeTroops={battle.own_contingent?.active}
          reserveTroops={battle.own_contingent?.reserve}
          morale={morale ?? undefined}
          reservePolicy={council.reservePolicy}
          onChangeReservePolicy={council.setReservePolicy}
          isSendingCommand={council.isSendingCommand}
          canCommitReserves={council.canCommitReserves && !council.isSendingCommand}
          onCommitReserves={() => void council.commitReserves()}
          canScout={council.canReconnoitre && !council.isSendingCommand}
          onOrderScout={(target) => void council.orderScoutMission(target)}
        />

        <WarCouncilRightPillar
          selectedTactic={council.stagedPlan.tactic}
          onSelectTactic={council.setActiveDoctrine}
          cavalryCount={battle.own_contingent?.troops["cavalry"] ?? 0}
          terrain={battle.terrain}
          frontlineCount={totalTroops}
          oddsBadgeText={odds ? `Odds: ${odds.tierText}` : "Odds: Unavailable"}
          isCommitting={council.isCommitting}
          isCommitDisabled={!council.canCommitWave}
          commitErrorMessage={council.commandErrorMessage}
          commitNoticeMessage={council.noticeMessage}
          onCommit={() => void council.commitWave()}
        />
      </div>

      <WarCouncilOverlays
        battle={battle}
        isCodexOpen={council.isCodexOpen}
        isRetreatOpen={council.isRetreatModalOpen}
        isWithdrawing={council.isSendingCommand}
        retreatErrorMessage={council.commandErrorMessage}
        receiptReport={council.receiptReport}
        morale={morale}
        isBattleResolved={battle.status === "resolved"}
        aftermath={council.aftermath}
        heldCaptives={battleCaptives}
        onCloseCodex={council.toggleCodex}
        onCancelRetreat={council.toggleRetreatModal}
        onConfirmRetreat={() => void handleConfirmRetreat()}
        onCloseReceipt={council.closeReceipt}
        onReturnToMap={onReturnToMap}
      />
    </main>
  );
}

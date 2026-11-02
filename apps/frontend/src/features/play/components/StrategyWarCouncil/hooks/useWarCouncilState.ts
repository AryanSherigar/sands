import { useCallback, useEffect, useMemo, useState } from "react";
import { useBattle } from "../../../hooks/useBattle";
import { useBattleCommands } from "../../../hooks/useBattleCommands";
import { useBattleReports } from "../../../hooks/useBattleReports";
import { useBattleSpeech } from "../../../hooks/useBattleSpeech";
import {
  buildAftermathSummary,
  findLatestReport,
} from "../../../lib/battleReports";
import type {
  BattleView,
  ExchangeReport,
  FormationType,
  ReservePolicyType,
  StandingPlan,
  TacticType,
  WardIdentifier,
} from "../StrategyWarCouncil.types";
import { useWardAllocation } from "./useWardAllocation";
import { useWarCouncilModals } from "./useWarCouncilModals";
import { calculateTacticalOdds } from "./useWarCouncilOdds";

const FALLBACK_PLAN: StandingPlan = {
  formation: "defensive",
  tactic: "hold",
  withdrawal_policy: "balanced",
  reserve_policy: "conserve",
};
const NOTICE_VISIBLE_MS = 4000;
const NO_REPORTS: ExchangeReport[] = [];
const BATTLE_LOAD_FAILED_MESSAGE = "The battle report could not be loaded.";

function canIssue(battle: BattleView | undefined, command: string): boolean {
  return battle?.legal_commands.includes(command) ?? false;
}

export function useWarCouncilState(
  playthroughId: string,
  battleId: string,
  initialBattle?: BattleView,
) {
  const battleQuery = useBattle(playthroughId, battleId, initialBattle);
  const reportsQuery = useBattleReports(playthroughId, battleId);
  const battle = battleQuery.data;
  const reports = reportsQuery.data ?? NO_REPORTS;

  const speech = useBattleSpeech(playthroughId, battleId);
  const commands = useBattleCommands({
    playthroughId,
    battleId,
    factionId: battle?.own_contingent?.faction_id ?? "",
  });

  const [planOverride, setPlanOverride] = useState<Partial<StandingPlan>>({});
  const [activeAnchor, setActiveAnchor] = useState<WardIdentifier>("center");
  const [receiptReport, setReceiptReport] = useState<ExchangeReport | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    if (!notice) return;
    const timer = setTimeout(() => setNotice(null), NOTICE_VISIBLE_MS);
    return () => clearTimeout(timer);
  }, [notice]);

  const { wards, updateCohortCount, reorderRank } = useWardAllocation();
  const modals = useWarCouncilModals();

  const stagedPlan: StandingPlan = useMemo(
    () => ({ ...(battle?.own_contingent?.plan ?? FALLBACK_PLAN), ...planOverride }),
    [battle?.own_contingent?.plan, planOverride],
  );

  const odds = useMemo(
    () => (battle ? calculateTacticalOdds(battle, stagedPlan) : null),
    [battle, stagedPlan],
  );

  const aftermath = useMemo(
    () => (battle && !receiptReport ? buildAftermathSummary(battle, reports) : null),
    [battle, reports, receiptReport],
  );

  const setFormation = useCallback((formation: FormationType) => {
    setPlanOverride((previous) => ({ ...previous, formation }));
  }, []);

  const setActiveDoctrine = useCallback((tactic: TacticType) => {
    setPlanOverride((previous) => ({ ...previous, tactic }));
  }, []);

  const setReservePolicy = useCallback((reserve_policy: ReservePolicyType) => {
    setPlanOverride((previous) => ({ ...previous, reserve_policy }));
  }, []);

  const commitWave = useCallback(async () => {
    const didCommit = await commands.commitWave(stagedPlan);
    if (!didCommit) return;
    const refreshed = await reportsQuery.refetch();
    setReceiptReport(findLatestReport(refreshed.data ?? []));
  }, [commands, stagedPlan, reportsQuery]);

  const confirmRetreat = useCallback(async (): Promise<boolean> => {
    const didWithdraw = await commands.withdraw();
    if (didWithdraw) modals.toggleRetreatModal();
    return didWithdraw;
  }, [commands, modals]);

  const orderScoutMission = useCallback(
    async (target: Parameters<typeof commands.reconnoitre>[1]): Promise<boolean> => {
      const opponent = battle?.opponents[0];
      if (!opponent) return false;
      const didSend = await commands.reconnoitre(opponent.faction_id, target);
      if (didSend) setNotice("Outriders dispatched.");
      return didSend;
    },
    [battle?.opponents, commands],
  );

  const commitReserves = useCallback(async (): Promise<boolean> => {
    const didCommit = await commands.commitReserves();
    if (didCommit) setNotice("Reserves committed.");
    return didCommit;
  }, [commands]);

  return {
    battle,
    isLoading: battleQuery.isLoading,
    loadErrorMessage: battleQuery.isError ? BATTLE_LOAD_FAILED_MESSAGE : null,
    retryLoad: battleQuery.refetch,
    reports,
    wards,
    reservePolicy: stagedPlan.reserve_policy,
    activeDoctrine: stagedPlan.tactic,
    stagedPlan,
    activeAnchor,
    odds,
    receiptReport,
    aftermath,
    isCommitting: commands.isCommitting,
    isSendingCommand: commands.isSendingCommand,
    commandErrorMessage: commands.errorMessage,
    canCommitWave: canIssue(battle, "set_plan"),
    canWithdraw: canIssue(battle, "withdraw"),
    canCommitReserves: canIssue(battle, "commit_reserves"),
    canReconnoitre: canIssue(battle, "reconnoitre"),
    canAddressTroops: canIssue(battle, "address_troops"),
    addressTroops: speech.address,
    speechReception: speech.reception,
    speechReactionLine: speech.reactionLine,
    speechErrorMessage: speech.errorMessage,
    isSpeaking: speech.isSending,
    isCodexOpen: modals.isCodexOpen,
    isRetreatModalOpen: modals.isRetreatModalOpen,
    updateCohortCount,
    reorderRank,
    setReservePolicy,
    setActiveDoctrine,
    setFormation,
    setAnchor: setActiveAnchor,
    commitWave,
    commitReserves,
    noticeMessage: notice,
    toggleCodex: modals.toggleCodex,
    toggleRetreatModal: modals.toggleRetreatModal,
    closeReceipt: () => setReceiptReport(null),
    orderScoutMission,
    confirmRetreat,
  };
}

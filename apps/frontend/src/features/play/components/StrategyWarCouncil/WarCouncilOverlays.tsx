import type { BattleView, ExchangeReport, NobleCaptive } from "./StrategyWarCouncil.types";
import type { BattleAftermathSummary } from "../../lib/battleReports";
import { BattleAftermathModal } from "./drawers/BattleAftermathModal";
import { CodexTacticsDrawer } from "./drawers/CodexTacticsDrawer";
import { ExchangeManuscriptModal } from "./drawers/ExchangeManuscriptModal";
import { RetreatModal } from "./drawers/RetreatModal";

export interface WarCouncilOverlaysProps {
  battle: BattleView;
  isCodexOpen: boolean;
  isRetreatOpen: boolean;
  isWithdrawing: boolean;
  retreatErrorMessage: string | null;
  receiptReport: ExchangeReport | null;
  morale: number | null;
  isBattleResolved: boolean;
  aftermath: BattleAftermathSummary | null;
  heldCaptives?: NobleCaptive[];
  onCloseCodex: () => void;
  onCancelRetreat: () => void;
  onConfirmRetreat: () => void;
  onCloseReceipt: () => void;
  onReturnToMap: () => void;
}

export function WarCouncilOverlays({
  battle,
  isCodexOpen,
  isRetreatOpen,
  isWithdrawing,
  retreatErrorMessage,
  receiptReport,
  morale,
  isBattleResolved,
  aftermath,
  heldCaptives,
  onCloseCodex,
  onCancelRetreat,
  onConfirmRetreat,
  onCloseReceipt,
  onReturnToMap,
}: WarCouncilOverlaysProps) {
  return (
    <>
      <CodexTacticsDrawer isOpen={isCodexOpen} battle={battle} onClose={onCloseCodex} />
      <RetreatModal
        isOpen={isRetreatOpen}
        onCancel={onCancelRetreat}
        onConfirm={onConfirmRetreat}
        isWithdrawing={isWithdrawing}
        errorMessage={retreatErrorMessage}
      />
      <ExchangeManuscriptModal
        report={receiptReport}
        morale={morale}
        isFinalWave={isBattleResolved}
        isOpen={Boolean(receiptReport)}
        onAdvanceWave={onCloseReceipt}
        onViewAftermath={onCloseReceipt}
      />
      {aftermath ? (
        <BattleAftermathModal
          isOpen
          aftermath={{
            outcome: aftermath.outcome,
            totalHostLosses: aftermath.totalOwnLosses,
            enemyStrengthRemaining: aftermath.enemyStrengthRemaining,
          }}
          nobleCaptives={heldCaptives}
          onReturnToRealmMap={onReturnToMap}
        />
      ) : null}
    </>
  );
}

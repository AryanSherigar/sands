export interface BattleReportActionsProps {
  regionId: string;
  roundsCount: number;
  isExpanded: boolean;
  onFocusMap?: () => void;
  onToggleRounds: () => void;
}

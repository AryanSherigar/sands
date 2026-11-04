import type { TableRegion } from "../../../../lib/tableRegions";

export interface NegotiationConsoleProps {
  regions?: TableRegion[];
  isDisabled?: boolean;
  hasPendingProposal?: boolean;
  isDrawerOpen?: boolean;
  isDeclinable?: boolean;
  isTreatyAvailable?: boolean;
  onSend: (text: string) => void;
  onToggleDrawer: () => void;
  onBreakTalks: () => void;
}

export interface StrategyChronicleBookProps {
  playthroughId?: string;
  rulerName: string;
  chroniclerId?: string | null;
  eraLabel: string;
  onClose: () => void;
}

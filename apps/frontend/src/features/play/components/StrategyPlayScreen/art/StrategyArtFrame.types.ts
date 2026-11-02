export interface StrategyArtFrameProps {
  artUrl: string | null;
  isLoading: boolean;
  altText: string;
  hasFailed?: boolean;
  canRetry?: boolean;
  onRetry?: () => void;
}

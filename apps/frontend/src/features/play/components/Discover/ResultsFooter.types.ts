export interface ResultsFooterProps {
  loadedCount: number;
  totalCount: number;
  hasNextPage: boolean;
  onLoadMore: () => void;
}

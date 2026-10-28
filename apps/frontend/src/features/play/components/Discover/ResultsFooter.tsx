import React from "react";
import { Button } from "@/shared/components/ui/Button";
import type { ResultsFooterProps } from "./ResultsFooter.types";

export const ResultsFooter: React.FC<ResultsFooterProps> = ({
  loadedCount,
  totalCount,
  hasNextPage,
  onLoadMore,
}) => (
  <div className="flex items-center justify-between gap-3 border-t border-border-subtle pt-6">
    <p className="font-mono text-xs text-content-faint">
      Showing {loadedCount} of {totalCount} scenarios
    </p>
    {hasNextPage && (
      <Button variant="secondary" size="sm" onClick={onLoadMore}>
        Load more
      </Button>
    )}
  </div>
);

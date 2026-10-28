import React, { useState } from "react";
import { Button } from "@/shared/components/ui/Button";
import { DataTable } from "./DataTable";
import type { ChartFigureProps } from "./ChartFigure.types";

export const ChartFigure: React.FC<ChartFigureProps> = ({
  title,
  summary,
  table,
  children,
}) => {
  const [isTableView, setIsTableView] = useState(false);
  const handleToggle = (): void => setIsTableView((current) => !current);
  return (
    <figure className="flex flex-col gap-3">
      <div className="flex items-start justify-between gap-4">
        <figcaption className="flex flex-col gap-1">
          <span className="font-sans text-sm font-semibold text-content">{title}</span>
          <span className="font-sans text-sm text-content-muted">{summary}</span>
        </figcaption>
        <Button variant="ghost" size="sm" onClick={handleToggle} aria-pressed={isTableView}>
          {isTableView ? "Show as chart" : "Show as table"}
        </Button>
      </div>
      {isTableView ? <DataTable table={table} caption={title} /> : children}
    </figure>
  );
};

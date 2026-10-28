import React from "react";
import { findMisfitLabels } from "../../../lib/comparisonFit";
import type { ComparisonFitNoteProps } from "./Advanced.types";

export const ComparisonFitNote: React.FC<ComparisonFitNoteProps> = ({ expression, metadata, options }) => {
  const labels = findMisfitLabels(expression, metadata, options);
  if (labels.length === 0) return null;

  return (
    <>
      {labels.map((label) => (
        <p key={label} className="text-meta text-danger">
          {`${label} no longer fits this comparison. Pick it again.`}
        </p>
      ))}
    </>
  );
};

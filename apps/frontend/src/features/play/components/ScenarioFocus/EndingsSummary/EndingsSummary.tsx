import React from "react";
import { SectionError } from "../SectionError/SectionError";
import { SignedInEndings } from "./SignedInEndings";
import { SignedOutEndings } from "./SignedOutEndings";
import type { EndingsSummaryProps } from "./EndingsSummary.types";

export const EndingsSummary: React.FC<EndingsSummaryProps> = ({
  endings,
  isError,
  onRetry,
}) => {
  if (isError) return <SectionError label="endings" onRetry={onRetry} />;
  if (!endings || endings.total_count === 0) return null;
  if (endings.found === null) {
    return <SignedOutEndings totalCount={endings.total_count} />;
  }
  return (
    <SignedInEndings totalCount={endings.total_count} found={endings.found} />
  );
};

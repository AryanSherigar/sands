import React from "react";
import { SectionHeading } from "../SectionHeading";

interface SignedOutEndingsProps {
  totalCount: number;
}

export const SignedOutEndings: React.FC<SignedOutEndingsProps> = ({
  totalCount,
}) => (
  <section aria-labelledby="scenario-endings-heading">
    <SectionHeading id="scenario-endings-heading" label="Endings" />
    <p className="font-sans text-sm text-content-muted">
      This story has {totalCount} {totalCount === 1 ? "ending" : "endings"}
    </p>
  </section>
);

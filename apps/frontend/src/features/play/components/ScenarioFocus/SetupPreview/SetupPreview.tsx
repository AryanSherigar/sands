import React from "react";
import { getSetupSummary } from "../../../utils/scenarioPage.utils";
import { SectionHeading } from "../SectionHeading";
import type { SetupPreviewProps } from "./SetupPreview.types";

const NO_SETUP_COPY = "No setup needed — jump straight in";

export const SetupPreview: React.FC<SetupPreviewProps> = ({ setupSchema }) => {
  const { requiredLabels, optionalCount, isQuickStart } =
    getSetupSummary(setupSchema);

  return (
    <section aria-labelledby="scenario-setup-heading">
      <SectionHeading id="scenario-setup-heading" label="Before you start" />
      <div className="rounded-md border border-border-subtle bg-surface-sunken p-5">
        {setupSchema.length === 0 ? (
          <p className="font-sans text-sm text-content-muted">{NO_SETUP_COPY}</p>
        ) : (
          <div className="space-y-2 font-sans text-sm">
            {requiredLabels.length > 0 && (
              <p className="text-content">
                You&apos;ll choose:{" "}
                <span className="text-content-muted">
                  {requiredLabels.join(", ")}
                </span>
              </p>
            )}
            {optionalCount > 0 && (
              <p className="text-content-faint">
                Plus {optionalCount} optional{" "}
                {optionalCount === 1 ? "detail" : "details"}
              </p>
            )}
            {isQuickStart && (
              <p className="text-content-muted">
                Nothing is required — you can start right away.
              </p>
            )}
          </div>
        )}
      </div>
    </section>
  );
};

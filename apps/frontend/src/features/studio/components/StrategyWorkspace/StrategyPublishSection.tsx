import React from "react";
import { Button } from "@/shared/components/ui/Button";
import { DEFAULT_CONTENT_TAG } from "../../constants/finish";
import { updateScenarioContentTag } from "../../api/scenarios.api";
import { usePublish } from "../../hooks/usePublish";
import type { PublishIssue } from "../../types/strategyDocument.types";
import type { StrategyPublishSectionProps } from "./StrategyWorkspace.types";

const MAP_MISSING_MESSAGE = "Import a map before publishing.";

const IssueList: React.FC<{ issues: PublishIssue[]; tone: string }> = ({ issues, tone }) => (
  <ul className={`list-disc space-y-1 pl-5 text-sm ${tone}`}>
    {issues.map((issue) => (
      <li key={`${issue.code}:${issue.path}:${issue.message}`}>{issue.message}</li>
    ))}
  </ul>
);

export const StrategyPublishSection: React.FC<StrategyPublishSectionProps> = ({
  scenario,
  report,
  isMapMissing,
  onFlush,
}) => {
  const flow = usePublish(scenario.scenario_id);
  const blocking = report?.blocking ?? [];
  const warnings = report?.warnings ?? [];
  const isBlocked = isMapMissing || blocking.length > 0 || report === undefined;
  const isBusy = flow.isTriggering || flow.isPolling;
  const failure = flow.triggerError ?? flow.publishError;

  const handlePublish = async (): Promise<void> => {
    await onFlush();
    if (!scenario.content_tag) {
      await updateScenarioContentTag(scenario.scenario_id, DEFAULT_CONTENT_TAG);
    }
    flow.publish();
  };

  return (
    <section className="space-y-3">
      <h2 className="text-lg font-semibold">4. Publish</h2>
      {isMapMissing && <p className="text-sm text-danger">{MAP_MISSING_MESSAGE}</p>}
      {blocking.length > 0 && <IssueList issues={blocking} tone="text-danger" />}
      {warnings.length > 0 && <IssueList issues={warnings} tone="text-content-muted" />}
      {failure && <p role="alert" className="text-sm text-danger">{failure}</p>}
      {flow.status === "published" && <p role="status" className="text-sm text-success">Published.</p>}
      <Button variant="primary" disabled={isBlocked || isBusy} onClick={handlePublish}>
        {isBusy ? "Publishing…" : "Publish"}
      </Button>
    </section>
  );
};

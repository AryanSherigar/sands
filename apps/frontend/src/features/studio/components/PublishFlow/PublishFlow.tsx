import React, { useState } from "react";
import { usePublish } from "../../hooks/usePublish";
import { updateScenarioContentTag } from "../../api/scenarios.api";
import { ContentTagPicker } from "@/shared/components/ContentTagPicker/ContentTagPicker";
import { ContentTag } from "@/shared/constants/content-tags";
import { extractErrorMessage } from "@/shared/lib/extractErrorMessage";
import { Button } from "@/shared/components/ui/Button";

export interface PublishFlowProps {
  scenarioId: string | null;
  onPublished?: () => void;
}

export const PublishFlow: React.FC<PublishFlowProps> = ({
  scenarioId,
  onPublished,
}) => {
  const [contentTag, setContentTag] = useState<ContentTag | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [isTaggingContent, setIsTaggingContent] = useState(false);

  const {
    status,
    isTriggering,
    isPolling,
    triggerError,
    publishError,
    publish,
  } = usePublish(scenarioId);

  const isBusy = isTaggingContent || isTriggering || isPolling;
  const errorMessage = validationError || triggerError || publishError;

  React.useEffect(() => {
    if (status === "published") {
      onPublished?.();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status]);

  const handlePublish = async () => {
    setValidationError(null);
    if (!scenarioId) {
      setValidationError("Save the scenario as a draft before publishing.");
      return;
    }
    if (!contentTag) {
      setValidationError("Select a content tag before publishing.");
      return;
    }

    setIsTaggingContent(true);
    try {
      await updateScenarioContentTag(scenarioId, contentTag);
    } catch (err: unknown) {
      setValidationError(
        extractErrorMessage(err, "Failed to save content tag."),
      );
      return;
    } finally {
      setIsTaggingContent(false);
    }

    publish();
  };

  const buttonLabel = () => {
    if (isTaggingContent) return "Saving Content Tag...";
    if (isTriggering) return "Starting...";
    if (isPolling) return "Publishing...";
    if (status === "published") return "Re-Publish";
    if (status === "publish_failed" || status === "draft") {
      return errorMessage ? "Retry Publish" : "Publish Scenario";
    }
    return "Publish Scenario";
  };

  return (
    <div className="space-y-6 border-t border-border-subtle pt-8">
      <ContentTagPicker
        value={contentTag}
        onChange={setContentTag}
        disabled={isBusy}
      />

      {errorMessage && (
        <div className="rounded-md p-4 bg-danger/10 border border-danger/40 text-danger text-sm font-mono">
          {errorMessage}
        </div>
      )}

      {status === "published" && !errorMessage && (
        <div className="rounded-md p-4 bg-success/10 border border-success/30 text-success text-sm font-mono">
          Scenario published — it is now live in discovery.
        </div>
      )}

      <Button
        type="button"
        variant="primary"
        onClick={handlePublish}
        disabled={isBusy}
      >
        {isBusy && (
          <span className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary-contrast mr-2" />
        )}
        {buttonLabel()}
      </Button>
    </div>
  );
};

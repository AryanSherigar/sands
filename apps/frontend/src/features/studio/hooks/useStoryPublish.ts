import { useState } from "react";
import { extractErrorMessage } from "@/shared/lib/extractErrorMessage";
import { DEFAULT_CONTENT_TAG, PUBLISH_FAILED_FALLBACK } from "../constants/finish";
import { useFirstPublishReveal } from "./useFirstPublishReveal";
import { useGuide } from "./useGuide";
import { usePublish } from "./usePublish";

export const useStoryPublish = () => {
  const { scenarioId, scenario, saveFields, flushSaves } = useGuide();
  const flow = usePublish(scenarioId);
  const [hasTriggered, setHasTriggered] = useState(false);
  const [isPreparing, setIsPreparing] = useState(false);
  const [prepareError, setPrepareError] = useState<string | null>(null);
  const hasJustPublished = hasTriggered && flow.status === "published";
  const reveal = useFirstPublishReveal(hasJustPublished);

  const publish = async (): Promise<void> => {
    if (!scenarioId) return;
    setPrepareError(null);
    setIsPreparing(true);
    try {
      if (!scenario?.content_tag) saveFields({ content_tag: DEFAULT_CONTENT_TAG });
      await flushSaves();
      await reveal.recordBaseline();
      setHasTriggered(true);
      flow.publish();
    } catch (error) {
      setPrepareError(extractErrorMessage(error, PUBLISH_FAILED_FALLBACK));
    } finally {
      setIsPreparing(false);
    }
  };

  const storedError = scenario?.status === "published" ? null : scenario?.publish_error;
  const failureMessage = prepareError ?? flow.triggerError ?? flow.publishError ?? storedError ?? null;

  return {
    publish,
    isBusy: isPreparing || flow.isTriggering || flow.isPolling,
    hasJustPublished,
    failureMessage,
    achievement: reveal.achievement,
  };
};

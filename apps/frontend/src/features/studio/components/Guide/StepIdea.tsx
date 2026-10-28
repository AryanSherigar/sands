import React from "react";
import {
  LOGLINE_MAX_LENGTH,
  TITLE_MAX_LENGTH,
} from "../../constants/guideLimits";
import { useGuide } from "../../hooks/useGuide";
import { useSyncedTextField } from "../../hooks/useSyncedTextField";
import { getGuideStep } from "../../lib/guideSteps";
import { GuideStepLayout } from "./GuideStepLayout";
import { GuideTextField } from "./GuideTextField";

const LOGLINE_PLACEHOLDER = "A lighthouse keeper finds a door in the sea.";

export const StepIdea: React.FC = () => {
  const { scenario, saveFields } = useGuide();
  const logline = useSyncedTextField(
    scenario?.logline ?? "",
    (next) => saveFields({ logline: next }),
    LOGLINE_MAX_LENGTH,
  );
  const title = useSyncedTextField(
    scenario?.title ?? "",
    (next) => saveFields({ title: next }),
    TITLE_MAX_LENGTH,
  );

  return (
    <GuideStepLayout step={getGuideStep("idea")}>
      <GuideTextField
        label="One line idea"
        helper="This shows on your story's card."
        placeholder={LOGLINE_PLACEHOLDER}
        maxLength={LOGLINE_MAX_LENGTH}
        value={logline.value}
        onChange={logline.onChange}
        isLarge
      />
      <GuideTextField
        label="What is the name of the story?"
        helper="No rush — you can name it later."
        maxLength={TITLE_MAX_LENGTH}
        value={title.value}
        onChange={title.onChange}
      />
    </GuideStepLayout>
  );
};

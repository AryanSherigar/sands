import React from "react";
import { ContentTagPicker } from "@/shared/components/ContentTagPicker/ContentTagPicker";
import { DEFAULT_CONTENT_TAG } from "../../constants/finish";
import { useGuide } from "../../hooks/useGuide";
import { useSyncedValue } from "../../hooks/useSyncedValue";

const LABEL = "Content warnings";
const DESCRIPTION = "Starts at All Ages. This never stops you from publishing.";

export const ContentWarningsSection: React.FC = () => {
  const { scenario, saveFields } = useGuide();
  const { value, commit } = useSyncedValue<string>(
    scenario?.content_tag ?? DEFAULT_CONTENT_TAG,
    (next) => saveFields({ content_tag: next }),
  );

  return (
    <ContentTagPicker value={value} onChange={commit} label={LABEL} description={DESCRIPTION} />
  );
};

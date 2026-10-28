import React from "react";
import { useGuide } from "../../hooks/useGuide";
import { CoverImageUploader } from "../CoverImageUploader/CoverImageUploader";

export const FinishCoverSection: React.FC = () => {
  const { scenario, saveFields } = useGuide();

  return (
    <CoverImageUploader
      label="Cover"
      description="No cover? We'll use this title cover."
      value={scenario?.cover_image_url ?? null}
      onChange={(url) => saveFields({ cover_image_url: url })}
      generatePrompt={{
        title: scenario?.title ?? "",
        genreTags: scenario?.genre_tags ?? [],
        openingScene: scenario?.opening_scene ?? undefined,
      }}
    />
  );
};

import React from "react";
import { Button } from "@/shared/components/ui/Button";
import { useCreateStory } from "@/shared/hooks/useCreateStory";
import { useIsAlphaMode } from "@/shared/hooks/useIsAlphaMode";

const ALPHA_EMPTY_COPY = "Check back soon.";
const CREATE_PROMPT_COPY = "Be the first to create one.";

export const LandingEmptyState: React.FC = () => {
  const handleCreate = useCreateStory();
  const isAlphaMode = useIsAlphaMode();

  return (
    <section className="flex min-h-[70vh] flex-col items-center justify-center gap-4 px-8 text-center">
      <h1 className="font-display text-4xl font-bold text-content">
        No stories published yet
      </h1>
      <p className="max-w-md font-sans text-base text-content-muted">
        {isAlphaMode ? ALPHA_EMPTY_COPY : CREATE_PROMPT_COPY}
      </p>
      {!isAlphaMode && (
        <Button
          variant="primary"
          size="lg"
          onClick={handleCreate}
          className="mt-2"
        >
          New Story
        </Button>
      )}
    </section>
  );
};

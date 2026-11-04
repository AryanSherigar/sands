import React from "react";
import { Button } from "@/shared/components/ui/Button";
import { useCreateStory } from "@/shared/hooks/useCreateStory";

const CREATE_PROMPT_COPY = "Be the first to create one.";

export const LandingEmptyState: React.FC = () => {
  const handleCreate = useCreateStory();

  return (
    <section className="flex min-h-[70vh] flex-col items-center justify-center gap-4 px-8 text-center">
      <h1 className="font-display text-4xl font-bold text-content">
        No stories published yet
      </h1>
      <p className="max-w-md font-sans text-base text-content-muted">
        {CREATE_PROMPT_COPY}
      </p>
      <Button
        variant="primary"
        size="lg"
        onClick={handleCreate}
        className="mt-2"
      >
        New Story
      </Button>
    </section>
  );
};

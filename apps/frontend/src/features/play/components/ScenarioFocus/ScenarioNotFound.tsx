import React from "react";
import { ButtonLink } from "@/shared/components/ui/ButtonLink";

export const ScenarioNotFound: React.FC = () => (
  <div className="flex flex-1 flex-col items-center justify-center gap-3 px-6 py-24 text-center">
    <h1 className="font-display text-2xl text-content">Story not found</h1>
    <p className="max-w-sm font-sans text-sm text-content-faint">
      It may have been unpublished, or the link is wrong.
    </p>
    <ButtonLink to="/discover" variant="secondary" className="mt-2">
      Explore stories
    </ButtonLink>
  </div>
);

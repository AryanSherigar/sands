import React from "react";
import { ButtonLink } from "@/shared/components/ui/ButtonLink";

export const ProfileNotFoundState: React.FC = () => (
  <div className="flex flex-col items-center gap-4 py-24 text-center">
    <h1 className="font-display text-3xl font-semibold text-content">
      This profile doesn&apos;t exist
    </h1>
    <p className="max-w-md text-sm text-content-muted">
      The link may be wrong, or the profile may have been removed.
    </p>
    <ButtonLink to="/discover" variant="secondary">
      Back to Discover
    </ButtonLink>
  </div>
);

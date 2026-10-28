import React from "react";
import { Button } from "@/shared/components/ui/Button";
import { ButtonLink } from "@/shared/components/ui/ButtonLink";
import {
  PUBLISHED_PRIVATE_MESSAGE,
  PUBLISHED_PUBLIC_MESSAGE,
  SCENARIO_PAGE_PATH_PREFIX,
} from "../../constants/finish";
import { STUDIO_LIST_PATH } from "../../constants/studioFrame";
import { useCopyToClipboard } from "../../hooks/useCopyToClipboard";
import { InvitePeoplePanel } from "./InvitePeoplePanel";
import type { PublishSuccessProps } from "./PublishSuccess.types";
import { WorldmakerReveal } from "./WorldmakerReveal";

const PLAY_PATH_PREFIX = "/setup/";

export const PublishSuccess: React.FC<PublishSuccessProps> = ({
  scenarioId,
  isPublic,
  achievement,
  onMakePublic,
  isMakingPublic,
  makePublicError,
}) => {
  const { copyState, copyText } = useCopyToClipboard();

  const handleCopyLink = (): void => {
    void copyText(`${window.location.origin}${SCENARIO_PAGE_PATH_PREFIX}${scenarioId}`);
  };

  return (
    <section aria-label="Published" className="space-y-4 rounded-lg border border-border-subtle bg-surface-raised p-4">
      <p role="status" className="text-heading font-semibold text-content">
        {isPublic ? PUBLISHED_PUBLIC_MESSAGE : PUBLISHED_PRIVATE_MESSAGE}
      </p>
      {achievement && <WorldmakerReveal achievement={achievement} />}
      <div className="flex flex-wrap items-center gap-2">
        <ButtonLink to={`${PLAY_PATH_PREFIX}${scenarioId}`} variant="primary">
          Play it
        </ButtonLink>
        <Button type="button" variant="secondary" onClick={handleCopyLink}>
          Copy link
        </Button>
        {!isPublic && (
          <Button type="button" variant="secondary" disabled={isMakingPublic} onClick={onMakePublic}>
            Make it public
          </Button>
        )}
        <ButtonLink to={STUDIO_LIST_PATH}>Back to Studio</ButtonLink>
      </div>
      {makePublicError && (
        <p role="alert" className="text-meta text-danger">
          {makePublicError}
        </p>
      )}
      {copyState === "copied" && (
        <p role="status" className="text-meta text-content-muted">
          Link copied
        </p>
      )}
      {copyState === "failed" && (
        <p role="alert" className="text-meta text-danger">
          Couldn't copy the link
        </p>
      )}
      {!isPublic && <InvitePeoplePanel scenarioId={scenarioId} />}
    </section>
  );
};

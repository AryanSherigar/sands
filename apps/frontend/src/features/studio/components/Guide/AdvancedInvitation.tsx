import React from "react";
import { Button } from "@/shared/components/ui/Button";
import { ADVANCED_NARROW_NOTICE } from "../../constants/advancedMode";
import { PUBLISHING_NOTICE } from "../../constants/studioFrame";
import type { AdvancedInvitationProps } from "./Guide.types";

export const AdvancedInvitation: React.FC<AdvancedInvitationProps> = ({
  canUseAdvanced,
  isPublishing,
  isBusy,
  onAccept,
  onDecline,
}) => (
  <section
    aria-label="Advanced mode"
    className="space-y-4 rounded-lg border border-border-subtle bg-surface-raised p-4"
  >
    <div className="space-y-1">
      <h3 className="text-heading font-semibold text-content">
        Your story is playable now. Want to turn on Advanced mode?
      </h3>
      <p className="text-meta text-content-muted">Endings, things to track, rules.</p>
      {!canUseAdvanced && (
        <p className="text-meta text-content-faint">{ADVANCED_NARROW_NOTICE}</p>
      )}
      {isPublishing && <p className="text-meta text-content-faint">{PUBLISHING_NOTICE}</p>}
    </div>
    <div className="flex flex-wrap justify-end gap-2">
      <Button type="button" variant="secondary" onClick={onDecline}>
        Not now
      </Button>
      {canUseAdvanced && (
        <Button type="button" disabled={isBusy || isPublishing} onClick={onAccept}>
          Turn on Advanced mode
        </Button>
      )}
    </div>
  </section>
);

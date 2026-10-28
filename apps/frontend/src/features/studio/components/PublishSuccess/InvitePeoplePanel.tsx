import React, { useState } from "react";
import { Button } from "@/shared/components/ui/Button";
import { useCopyToClipboard } from "../../hooks/useCopyToClipboard";
import { useScenarioAccess } from "../../hooks/useScenarioAccess";
import type { InvitePeoplePanelProps } from "./PublishSuccess.types";

const INVITE_LINK_LABEL = "Invite link";

export const InvitePeoplePanel: React.FC<InvitePeoplePanelProps> = ({ scenarioId }) => {
  const access = useScenarioAccess(scenarioId);
  const { copyState, copyText } = useCopyToClipboard();
  const [inviteUrl, setInviteUrl] = useState<string | null>(null);

  const handleInvite = async (): Promise<void> => {
    const invite = await access.createInviteAsync().catch(() => null);
    if (invite) setInviteUrl(invite.url);
  };
  const handleCopyInvite = (): void => {
    if (inviteUrl) void copyText(inviteUrl);
  };

  return (
    <div className="space-y-3">
      <Button type="button" variant="secondary" disabled={access.isCreatingInvite} onClick={() => void handleInvite()}>
        Invite people
      </Button>
      {access.inviteError && (
        <p role="alert" className="text-meta text-danger">
          {access.inviteError}
        </p>
      )}
      {inviteUrl && (
        <div className="flex items-center gap-2">
          <input
            readOnly
            aria-label={INVITE_LINK_LABEL}
            value={inviteUrl}
            onFocus={(event) => event.target.select()}
            className="min-w-0 flex-1 rounded-sm border border-border-strong bg-surface-inset px-2 py-1.5 text-meta text-content"
          />
          <Button type="button" size="sm" onClick={handleCopyInvite}>
            Copy invite link
          </Button>
        </div>
      )}
      {copyState === "failed" && (
        <p role="alert" className="text-meta text-danger">
          Couldn't copy. Select the link and copy it yourself.
        </p>
      )}
      {inviteUrl && (
        <p className="text-micro text-content-faint">Each link works once and expires after a few days.</p>
      )}
      {access.members.length > 0 && (
        <ul aria-label="People who can play" className="space-y-1">
          {access.members.map((member) => (
            <li key={member.user_id} className="flex items-center justify-between gap-2 text-meta text-content">
              <span>{member.display_name}</span>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                aria-label={`Remove ${member.display_name}`}
                disabled={access.isRemovingAccess}
                onClick={() => access.removeAccess(member.user_id)}
              >
                Remove
              </Button>
            </li>
          ))}
        </ul>
      )}
      {access.removeError && (
        <p role="alert" className="text-meta text-danger">
          {access.removeError}
        </p>
      )}
    </div>
  );
};

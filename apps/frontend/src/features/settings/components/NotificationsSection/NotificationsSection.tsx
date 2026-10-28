import React from "react";
import { IconBellOff } from "@tabler/icons-react";

export const NotificationsSection: React.FC = () => (
  <div className="flex gap-4 rounded-md border border-border-subtle bg-surface-raised p-5">
    <IconBellOff size={20} stroke={1.5} aria-hidden="true" className="mt-0.5 shrink-0 text-content-faint" />
    <div className="space-y-1">
      <p className="font-sans text-sm text-content-muted">
        Email digests, campaign activity summaries and browser notifications
        are in development.
      </p>
      <p className="font-sans text-xs text-content-faint">
        We do not send promotional or marketing emails. Future notifications
        will be strictly transactional or fiction-related.
      </p>
    </div>
  </div>
);

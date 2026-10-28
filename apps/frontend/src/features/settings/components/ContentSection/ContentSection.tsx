import React from "react";
import { IconInfoCircle } from "@tabler/icons-react";
import { CONTENT_TAG_LABELS } from "@/shared/constants/content-tags";
import { MatureContentToggle } from "../MatureContentToggle/MatureContentToggle";

const CONTENT_TAG_EXPLANATIONS: Record<keyof typeof CONTENT_TAG_LABELS, string> = {
  "all-ages": "Suitable for everyone.",
  teen: "May include mild violence or themes better suited to teens and up.",
  mature: "Intended for adults; may include graphic violence or strong language.",
};

export const ContentSection: React.FC = () => (
  <div className="space-y-4 rounded-md border border-border-subtle bg-surface-raised p-5">
    <MatureContentToggle />
    <div className="space-y-3 rounded-md border border-border-subtle bg-surface-inset p-4">
      <h3 className="flex items-center gap-2 font-sans text-sm font-medium text-content">
        <IconInfoCircle size={16} stroke={1.5} aria-hidden="true" />
        Content ratings
      </h3>
      <dl className="space-y-2 font-sans text-xs">
        {Object.entries(CONTENT_TAG_EXPLANATIONS).map(([tag, explanation]) => (
          <div key={tag} className="flex gap-3">
            <dt className="w-20 shrink-0 font-semibold text-content">
              {CONTENT_TAG_LABELS[tag as keyof typeof CONTENT_TAG_LABELS]}
            </dt>
            <dd className="text-content-muted">{explanation}</dd>
          </div>
        ))}
      </dl>
    </div>
  </div>
);

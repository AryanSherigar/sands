import React from "react";
import type { SetupPreviewProps } from "./Guide.types";

export const SetupPreview: React.FC<SetupPreviewProps> = ({ fields }) => (
  <div
    role="region"
    aria-label="Setup screen preview"
    className="space-y-4 rounded-lg border border-border-subtle bg-surface-inset p-4"
  >
    <p className="text-micro text-content-faint">What players see before they start</p>
    {fields.length === 0 && (
      <p className="text-meta text-content-muted">Players start right away.</p>
    )}
    {fields.map((field) => (
      <div key={field.id} className="space-y-1">
        <p className="text-meta font-medium text-content">{field.label || "Untitled question"}</p>
        {field.options.length > 0 ? (
          <p className="text-micro text-content-muted">
            {field.options.map((option) => option.label).join(" · ")}
          </p>
        ) : (
          <div className="h-9 rounded-sm border border-border-strong bg-surface" />
        )}
      </div>
    ))}
  </div>
);

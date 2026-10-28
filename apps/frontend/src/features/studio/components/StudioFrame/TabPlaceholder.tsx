import React from "react";

export const TabPlaceholder: React.FC<{ label: string }> = ({ label }) => (
  <div className="mx-auto w-full max-w-[640px] px-4 py-12">
    <p className="rounded-md border border-dashed border-border-strong p-4 text-meta text-content-muted">
      {label} isn't available yet.
    </p>
  </div>
);

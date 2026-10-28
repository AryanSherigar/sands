import React from "react";
import { IconEye, IconInfoCircle } from "@tabler/icons-react";
import { SegmentedControl } from "../SegmentedControl/SegmentedControl";
import { useProfilePreviewStore } from "../../stores/profilePreview.store";

type ViewerMode = "owner" | "visitor";

const VIEWER_OPTIONS: { value: ViewerMode; label: string }[] = [
  { value: "owner", label: "Owner (You)" },
  { value: "visitor", label: "Public Visitor" },
];

export const ViewingAsBar: React.FC = () => {
  const isPreviewingAsVisitor = useProfilePreviewStore(
    (state) => state.isPreviewingAsVisitor,
  );
  const setPreviewingAsVisitor = useProfilePreviewStore(
    (state) => state.setPreviewingAsVisitor,
  );

  const handleModeChange = (mode: ViewerMode) => {
    setPreviewingAsVisitor(mode === "visitor");
  };

  return (
    <div className="hidden items-center justify-between gap-4 border-b border-border-subtle py-3 md:flex">
      <div className="flex items-center gap-3 text-sm text-content-muted">
        <IconEye size={20} stroke={1.5} aria-hidden="true" />
        <span>Viewing as</span>
        <SegmentedControl
          ariaLabel="Viewing as"
          options={VIEWER_OPTIONS}
          value={isPreviewingAsVisitor ? "visitor" : "owner"}
          onChange={handleModeChange}
        />
      </div>
      <p className="flex items-center gap-2 text-xs text-content-faint">
        <IconInfoCircle size={16} stroke={1.5} aria-hidden="true" />
        Owner view reveals private runs, saved stories and personal stats.
      </p>
    </div>
  );
};

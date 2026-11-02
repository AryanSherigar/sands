import { IconGripVertical } from "@tabler/icons-react";
import type { FantasyDossierResizerProps } from "./FantasyDossierResizer.types";

export function FantasyDossierResizer({
  sidebarWidth,
  minWidth,
  maxWidth,
  isDragging,
  onStartDrag,
  onKeyDown,
}: FantasyDossierResizerProps) {
  return (
    <div
      role="separator"
      tabIndex={0}
      aria-label="Resize Crown Dossier"
      aria-orientation="vertical"
      aria-valuenow={sidebarWidth}
      aria-valuemin={minWidth}
      aria-valuemax={maxWidth}
      onMouseDown={onStartDrag}
      onTouchStart={onStartDrag}
      onKeyDown={onKeyDown}
      className={`hidden xl:flex items-center justify-center absolute left-0 top-0 bottom-0 -ml-1.5 w-3 cursor-col-resize z-50 group select-none ${
        isDragging ? "pointer-events-auto" : ""
      }`}
    >
      <div
        className={`w-[2px] h-full transition-colors duration-150 ${
          isDragging
            ? "bg-[#C5A059] shadow-[0_0_8px_rgba(197,160,89,0.5)]"
            : "bg-transparent group-hover:bg-[#C5A059]/60"
        }`}
      />
      <div
        className={`absolute w-3.5 h-10 rounded-full border flex items-center justify-center transition-all duration-150 shadow-md ${
          isDragging
            ? "bg-[#2A2016] border-[#C5A059] text-[#F2DCA2] scale-105"
            : "bg-[#181410] border-[#3E3224] text-[#8C7A6B] group-hover:border-[#C5A059] group-hover:text-[#F2DCA2]"
        }`}
      >
        <IconGripVertical size={11} />
      </div>
    </div>
  );
}

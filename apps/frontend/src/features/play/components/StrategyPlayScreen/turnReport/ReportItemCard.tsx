import React from "react";
import {
  IconBuilding,
  IconCoin,
  IconMapPin,
  IconSwords,
  IconUsers,
} from "@tabler/icons-react";
import type { ReportItemCardProps } from "./ReportItemCard.types";
import type { ItemTone, ReportItem } from "../../../types/turnReport.types";

const getToneClass = (tone?: ItemTone): string => {
  switch (tone) {
    case "positive":
      return "bg-[#5E8A5A]/15 text-[#3E653A] border-[#5E8A5A]/30";
    case "warning":
      return "bg-[#D2A94A]/20 text-[#8B6B1B] border-[#D2A94A]/40";
    case "danger":
      return "bg-[#A8483E]/15 text-[#88362D] border-[#A8483E]/30";
    case "neutral":
    default:
      return "bg-[#46606E]/15 text-[#304B59] border-[#46606E]/30";
  }
};

const renderCategoryIcon = (category: ReportItem["category"]) => {
  switch (category) {
    case "military":
      return <IconSwords size={14} className="text-[#A8483E]" />;
    case "economy":
      return <IconCoin size={14} className="text-[#D2A94A]" />;
    case "diplomacy":
      return <IconUsers size={14} className="text-[#46606E]" />;
    case "internal":
      return <IconBuilding size={14} className="text-[#7A6F62]" />;
  }
};

export const ReportItemCard: React.FC<ReportItemCardProps> = ({
  item,
  onFocusMap,
}) => {
  const handleFocus = () => item.regionId && onFocusMap?.(item.regionId);

  return (
    <article className="p-3 bg-[#F3EAD3]/70 rounded-lg border border-[#3A3128]/20 space-y-2">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-1.5">
          {renderCategoryIcon(item.category)}
          <h4 className="font-serif font-semibold text-sm text-[#3A3128]">
            {item.title}
          </h4>
        </div>
        <div className="flex items-center gap-1.5">
          {item.signedValue ? (
            <span className="text-xs font-mono font-medium text-[#3A3128]">
              {item.signedValue}
            </span>
          ) : null}
          {item.badge ? (
            <span
              className={`px-2 py-0.5 text-[11px] font-medium rounded border ${getToneClass(item.badge.tone)}`}
            >
              {item.badge.label}
            </span>
          ) : null}
        </div>
      </div>

      <p className="text-xs text-[#55493E] leading-relaxed">{item.description}</p>

      {item.regionId && onFocusMap ? (
        <div className="pt-1">
          <button
            type="button"
            onClick={handleFocus}
            className="flex items-center gap-1 text-xs text-[#46606E] hover:text-[#304B59] font-medium cursor-pointer"
            aria-label="Show on map"
          >
            <IconMapPin size={13} />
            <span>Show on map</span>
          </button>
        </div>
      ) : null}
    </article>
  );
};

import React from "react";
import { IconFeather, IconSparkles } from "@tabler/icons-react";
import type { ChronicleBackstoryFieldProps } from "./ChronicleBackstoryField.types";

function RedraftButton({
  isRedrafting,
  onClick,
}: {
  isRedrafting: boolean;
  onClick: () => void;
}) {
  const buttonClasses = isRedrafting
    ? "flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#785a00]/20 text-[#785a00] font-medium text-xs cursor-wait animate-pulse"
    : "group flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#2e4856]/10 hover:bg-[#2e4856]/20 text-[#2e4856] transition-colors text-xs font-medium";

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={isRedrafting}
      className={buttonClasses}
    >
      <IconSparkles
        size={14}
        className={isRedrafting ? "animate-spin" : "group-hover:rotate-12 transition-transform"}
      />
      <span>{isRedrafting ? "Inscribing with Chronicler..." : "✦ Redraft Backstory with AI"}</span>
    </button>
  );
}

export const ChronicleBackstoryField: React.FC<ChronicleBackstoryFieldProps> = ({
  backstory,
  isRedrafting,
  onChangeBackstory,
  onRedraft,
  chronicleYearLabel = "Anno 1042 Chronicle Entry",
}) => {
  const handleTextChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    onChangeBackstory(e.target.value);
  };

  return (
    <div className="bg-[#F7F0DC]/90 backdrop-blur-md p-4 rounded-xl shadow-md border border-[#3A3128]/15 flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <IconFeather size={18} className="text-[#785a00]" />
          <h3 className="font-serif text-lg font-semibold text-[#221a12]">
            The Royal Chronicle &amp; Lineage
          </h3>
        </div>
        <RedraftButton isRedrafting={isRedrafting} onClick={onRedraft} />
      </div>
      <div className="relative">
        <textarea
          className="w-full bg-white/80 text-[#221a12] font-serif text-[17px] leading-relaxed p-3 pb-7 rounded shadow-sm focus:outline-none focus:ring-2 focus:ring-[#2e4856] resize-none"
          rows={3}
          value={backstory}
          onChange={handleTextChange}
          placeholder="Inscribe the deeds and origin of your sovereign..."
          disabled={isRedrafting}
        />
        <div className="absolute bottom-2 right-2 text-right pointer-events-none">
          <span className="text-[10px] text-[#72787c] font-medium">{chronicleYearLabel}</span>
        </div>
      </div>
    </div>
  );
};

import React from "react";
import { IconCrown, IconEdit, IconShieldCheck } from "@tabler/icons-react";
import type { SovereignIdentityCardProps } from "./SovereignIdentityCard.types";

const FALLBACK_PORTRAIT =
  "https://lh3.googleusercontent.com/aida-public/AB6AXuBsacY1r5pJ5gGVLUhuFAS4mQ99oLQChktAGMvSurMx4VOYhLC8X03qb7vxRY2dO_2fkBtAoi9tpmFzz53n7iIvFsZQsl2iWYNnCVMdhY7KBnHfllM2bErsuc1RD7Regn4Ew1aWlFZqiiKt3ZmmkhPjWHDR7zLNMIcx6HESEoDDMY-z-IIAT0yvuDUsbzvh7jqWYjDgR1__74fe8wTjh9JBd8D2VkY-ucF7BH9Cx0WMGbP8FqhUM6Re-g";

function SovereignPortrait({ portraitUrl }: { portraitUrl?: string }) {
  const imageSource = portraitUrl || FALLBACK_PORTRAIT;
  return (
    <div className="relative shrink-0">
      <div className="w-28 h-36 rounded-t-full rounded-b-lg overflow-hidden shadow-md bg-[#f5e5d8] p-1">
        <div className="w-full h-full rounded-t-full rounded-b-md overflow-hidden relative">
          <img
            className="w-full h-full object-cover"
            alt="Sovereign Coronation Portrait"
            src={imageSource}
          />
          <div className="absolute inset-0 bg-gradient-to-t from-[#2e4856]/30 to-transparent pointer-events-none" />
        </div>
      </div>
      <div className="absolute -bottom-2 -right-1 w-8 h-8 rounded-full bg-[#785a00] text-white shadow-md flex items-center justify-center">
        <IconCrown size={16} />
      </div>
    </div>
  );
}

function DynastyBadge({ dynastyName, houseMotto }: { dynastyName?: string; houseMotto?: string }) {
  const resolvedDynasty = dynastyName || "House of Highgard • Anno 988–";
  const resolvedMotto = houseMotto || "Though Mists Envelop, We Stand";
  return (
    <div className="flex items-center justify-between pt-1">
      <span className="text-xs text-[#42474b] flex items-center gap-1.5 font-medium">
        <IconShieldCheck size={16} className="text-[#785a00]" />
        {resolvedDynasty}
      </span>
      <span className="text-[11px] text-[#72787c] italic">“{resolvedMotto}”</span>
    </div>
  );
}

export const SovereignIdentityCard: React.FC<SovereignIdentityCardProps> = ({
  name,
  epithet,
  portraitUrl,
  dynastyName,
  houseMotto,
  onChangeName,
  onChangeEpithet,
}) => {
  const handleNameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onChangeName(e.target.value);
  };

  const handleEpithetChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onChangeEpithet(e.target.value);
  };

  return (
    <div className="bg-[#F7F0DC]/90 backdrop-blur-md p-4 rounded-xl shadow-md border border-[#3A3128]/15 flex flex-col sm:flex-row items-center sm:items-start gap-4">
      <SovereignPortrait portraitUrl={portraitUrl} />
      <div className="flex-1 w-full flex flex-col gap-2">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          <div className="flex flex-col gap-1">
            <label className="text-[11px] uppercase tracking-wider text-[#72787c] font-semibold" htmlFor="sovereignName">
              Regnal Name
            </label>
            <div className="relative">
              <input
                className="w-full bg-white/80 text-[#221a12] font-serif text-[18px] px-3 py-1.5 rounded shadow-sm focus:outline-none focus:ring-2 focus:ring-[#2e4856]"
                id="sovereignName"
                type="text"
                value={name}
                onChange={handleNameChange}
              />
              <IconEdit size={16} className="absolute right-2 top-2 text-[#72787c] pointer-events-none" />
            </div>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-[11px] uppercase tracking-wider text-[#72787c] font-semibold" htmlFor="sovereignTitle">
              Coronation Epithet
            </label>
            <input
              className="w-full bg-white/80 text-[#221a12] font-serif text-[15px] px-3 py-1.5 rounded shadow-sm focus:outline-none focus:ring-2 focus:ring-[#2e4856]"
              id="sovereignTitle"
              type="text"
              value={epithet}
              onChange={handleEpithetChange}
            />
          </div>
        </div>
        <DynastyBadge dynastyName={dynastyName} houseMotto={houseMotto} />
      </div>
    </div>
  );
};

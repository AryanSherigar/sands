import React from "react";
import {
  IconCompass,
  IconShield,
  IconTrees,
  IconSwords,
  IconSailboat,
} from "@tabler/icons-react";
import type { StrategySetupMapProps, PlayableFactionInfo } from "./StrategyRulerSetup.types";
import { FALLBACK_STRATEGY_MAP } from "../StrategyPlayScreen/fallbackStrategyMap";
import type { MapRegion } from "@/shared/types/strategy-map.types";

const DEFAULT_MAP_BG =
  "https://lh3.googleusercontent.com/aida-public/AB6AXuA3wl03TneYGCeEOVoL1w2XjPBTYNi9wFIL3cxJHz0JmBNvErkl69agyHGmDgFw5F2p0L411xU9GrzGRrGyuyZl5t7Zl3ESKh3AzWKiu8u1vLHts6SZjD6Tip7fQ33ncjEgT1gkv-HQlbsX3X0Ae6KoI9RJ3xNMH3s-fdf0X4nFifwH420sLVjWcobKJg695N2B8HnljWOEUvb6o9yyNqG-szEkXUX8_r7buMlIf162ueVCm64Az86f2g";

const FALLBACK_PIN_COORDS = [
  { x: 780, y: 430 },
  { x: 540, y: 490 },
  { x: 1170, y: 250 },
  { x: 370, y: 340 },
];

function getFactionIcon(factionId: string) {
  const id = factionId.toLowerCase();
  if (id.includes("oak") || id.includes("forest") || id.includes("green")) {
    return <IconTrees size={13} />;
  }
  if (id.includes("iron") || id.includes("martial") || id.includes("vanguard")) {
    return <IconSwords size={13} />;
  }
  if (id.includes("river") || id.includes("trade") || id.includes("sail") || id.includes("water")) {
    return <IconSailboat size={13} />;
  }
  return <IconShield size={14} />;
}

function getShortName(fullName: string): string {
  return fullName.replace(/^(Crown of|Duchy of|March of|Freehold of)\s+/i, "");
}

export const StrategySetupMap: React.FC<StrategySetupMapProps> = ({
  mapDoc = FALLBACK_STRATEGY_MAP,
  factions,
  activeFactionId,
  onSelectFaction,
}) => {
  const activeDoc = mapDoc ?? FALLBACK_STRATEGY_MAP;
  const width = activeDoc.width || 1600;
  const height = activeDoc.height || 900;
  const regions = activeDoc.regions || [];

  // Map each region to a faction
  const getRegionFaction = (region: MapRegion, index: number): PlayableFactionInfo | undefined => {
    // 1. Direct capital match
    const byCapital = factions.find((f) => f.capital_region_id === region.id);
    if (byCapital) return byCapital;

    // 2. Name / ID match
    const regLower = (region.name + " " + region.id).toLowerCase();
    const byName = factions.find((f) => {
      const fId = f.id.toLowerCase();
      if (fId.includes("valen") && regLower.includes("dunmere")) return true;
      if (fId.includes("oak") && regLower.includes("greenford")) return true;
      if (fId.includes("iron") && regLower.includes("highcrag")) return true;
      if (fId.includes("river") && regLower.includes("silverwood")) return true;
      return regLower.includes(fId);
    });
    if (byName) return byName;

    // 3. Round-robin fallback
    return factions[index % factions.length];
  };

  // Determine pin coordinate for each faction
  const factionPins = factions.map((faction, idx) => {
    let pinX = FALLBACK_PIN_COORDS[idx % FALLBACK_PIN_COORDS.length].x;
    let pinY = FALLBACK_PIN_COORDS[idx % FALLBACK_PIN_COORDS.length].y;

    const matchedRegion = regions.find((r, rIdx) => {
      const rFaction = getRegionFaction(r, rIdx);
      return rFaction?.id === faction.id;
    });

    if (matchedRegion?.label_point) {
      pinX = matchedRegion.label_point.x;
      pinY = matchedRegion.label_point.y;
    }

    return {
      faction,
      x: pinX,
      y: pinY,
      isActive: faction.id === activeFactionId,
    };
  });

  return (
    <div className="relative w-full h-[340px] rounded-xl overflow-hidden shadow-md bg-[#f5e5d8]/60 group border border-[#3A3128]/15">
      {/* Hand-painted Watercolor Map Texture Background */}
      <div
        className="absolute inset-0 bg-cover bg-center w-full h-full transform transition-transform duration-700 group-hover:scale-[1.02]"
        style={{ backgroundImage: `url('${activeDoc.image_url || DEFAULT_MAP_BG}')` }}
      />

      {/* Atmospheric Cloud Vignette Overlay */}
      <div className="absolute inset-0 bg-gradient-to-t from-[#F3EAD3]/90 via-transparent to-[#F3EAD3]/40 pointer-events-none" />

      {/* Interactive SVG Territories */}
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="absolute inset-0 w-full h-full pointer-events-auto"
        preserveAspectRatio="none"
      >
        <g className="regions">
          {regions.map((region, idx) => {
            const ownerFaction = getRegionFaction(region, idx);
            const isOwnerActive = ownerFaction?.id === activeFactionId;
            return (
              <path
                key={region.id}
                d={region.outline}
                fill={ownerFaction ? ownerFaction.color : "#46606E"}
                fillOpacity={isOwnerActive ? 0.42 : 0.22}
                stroke="#3A3128"
                strokeWidth={isOwnerActive ? 2 : 1}
                strokeOpacity={isOwnerActive ? 0.85 : 0.45}
                className="transition-all duration-300 cursor-pointer hover:fill-opacity-50"
                onClick={() => ownerFaction && onSelectFaction(ownerFaction.id)}
              >
                <title>{`${region.name} (${ownerFaction?.name ?? "Neutral Territory"})`}</title>
              </path>
            );
          })}
        </g>
      </svg>

      {/* Compass Rose Stamp (Top Left Corner) */}
      <div className="absolute top-4 left-4 p-2 bg-[#F7F0DC]/80 backdrop-blur-sm rounded-lg shadow-sm flex items-center gap-2 pointer-events-none border border-[#3A3128]/10 z-10">
        <IconCompass size={22} className="text-[#785a00] shrink-0" />
        <div className="flex flex-col">
          <span className="text-[10px] uppercase font-semibold text-[#72787c] tracking-wider font-['Manrope',sans-serif]">
            The Frontier Wilds
          </span>
          <span className="text-[11px] font-bold text-[#221a12] font-['Manrope',sans-serif] tabular-nums">
            E. 42° 11′ · N. 18° 04′
          </span>
        </div>
      </div>

      {/* Capital Pins */}
      {factionPins.map(({ faction, x, y, isActive }) => {
        const leftPercent = (x / width) * 100;
        const topPercent = (y / height) * 100;
        const shortName = getShortName(faction.name);
        const provinceCount = faction.provinces_count ?? 1;

        return (
          <div
            key={faction.id}
            data-testid={`map-pin-${faction.id}`}
            role="button"
            tabIndex={0}
            onClick={() => onSelectFaction(faction.id)}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onSelectFaction(faction.id);
              }
            }}
            aria-label={`Select ${faction.name}`}
            className="absolute -translate-x-1/2 -translate-y-1/2 cursor-pointer group/pin z-20"
            style={{ left: `${leftPercent}%`, top: `${topPercent}%` }}
          >
            <div className="relative flex items-center justify-center">
              {isActive && (
                <span
                  className="absolute w-8 h-8 rounded-full animate-ping pointer-events-none"
                  style={{ backgroundColor: faction.color, opacity: 0.35 }}
                />
              )}
              <span
                className="w-6 h-6 rounded-full flex items-center justify-center shadow-md text-white transition-transform group-hover/pin:scale-110"
                style={{ backgroundColor: faction.color }}
              >
                {getFactionIcon(faction.id)}
              </span>
            </div>

            {/* Pin Callout Box */}
            <div
              className={`absolute left-7 -top-2 bg-[#F7F0DC]/95 backdrop-blur-md px-2 py-0.5 rounded shadow-md whitespace-nowrap border border-[#3A3128]/10 pointer-events-none transition-opacity ${
                isActive ? "opacity-100" : "opacity-0 group-hover/pin:opacity-100"
              }`}
            >
              <span
                className="text-[13px] font-semibold block leading-tight font-['EB_Garamond',serif]"
                style={{ color: faction.color }}
              >
                {shortName}
              </span>
              <span className="text-[10px] text-[#42474b] font-['Manrope',sans-serif]">
                {provinceCount} Fertile {provinceCount === 1 ? "Province" : "Provinces"}
              </span>
            </div>
          </div>
        );
      })}

      {/* Map Key Legend Floating Pill */}
      <div className="absolute bottom-3 right-3 bg-[#F7F0DC]/90 backdrop-blur-sm px-3 py-1 rounded-full shadow-sm flex items-center gap-3 border border-[#3A3128]/10 z-10">
        {factions.map((f) => {
          const isCurrent = f.id === activeFactionId;
          return (
            <button
              key={f.id}
              type="button"
              data-testid={`map-legend-${f.id}`}
              onClick={() => onSelectFaction(f.id)}
              className={`flex items-center gap-1.5 cursor-pointer transition-opacity ${
                isCurrent ? "opacity-100 font-bold" : "opacity-75 hover:opacity-100"
              }`}
            >
              <span
                className="w-2.5 h-2.5 rounded-full shrink-0"
                style={{ backgroundColor: f.color }}
              />
              <span className="text-[11px] text-[#221a12] font-['Manrope',sans-serif] whitespace-nowrap">
                {getShortName(f.name)}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
};

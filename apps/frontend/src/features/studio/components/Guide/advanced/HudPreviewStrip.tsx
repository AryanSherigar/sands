import React from "react";
import { ShiftClockBadge } from "@/shared/components/status-hud/ShiftClockBadge";
import { StatusHud } from "@/shared/components/status-hud/StatusHud";
import { formatClock } from "@/shared/lib/hud/formatClock";
import { readDisplayHints } from "@/shared/lib/hud/readDisplayHints";
import { resolveMeterTier } from "@/shared/lib/hud/resolveMeterTier";
import type { HudPreviewStripProps } from "./Advanced.types";

const readInitialNumber = (schema: HudPreviewStripProps["schema"], path: string, fallback: number): number => {
  const initial = schema[path]?.initial;
  return typeof initial === "number" ? initial : fallback;
};

export const HudPreviewStrip: React.FC<HudPreviewStripProps> = ({ schema }) => {
  const hints = readDisplayHints(schema);
  const { clock, meters, tier } = hints;
  if (!clock && meters.length === 0 && !tier) return null;

  const meterProps = meters.map(({ path, hint }) => {
    const value = readInitialNumber(schema, path, hint.clamp_max);
    return {
      label: hint.label,
      value,
      clampMin: hint.clamp_min,
      clampMax: hint.clamp_max,
      tierName: resolveMeterTier(hint.tiers, value),
      shouldAnimate: false,
    };
  });
  const tierProps = tier ? { label: tier.hint.label, options: tier.options, value: tier.options[0] ?? "" } : null;

  return (
    <section
      aria-label="What the player sees"
      className="flex flex-wrap items-center gap-x-6 gap-y-2 rounded-md border border-border-subtle bg-surface-inset px-4 py-3"
    >
      {clock && (
        <ShiftClockBadge
          label={clock.hint.label}
          time={formatClock(readInitialNumber(schema, clock.path, 0), clock.hint.start, clock.hint.format)}
        />
      )}
      <StatusHud meters={meterProps} tier={tierProps} />
    </section>
  );
};

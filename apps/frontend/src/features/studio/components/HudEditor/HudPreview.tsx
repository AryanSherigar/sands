import React, { useState } from "react";
import { ShiftClockBadge } from "@/shared/components/status-hud/ShiftClockBadge";
import { StatusHud } from "@/shared/components/status-hud/StatusHud";
import { formatClock } from "@/shared/lib/hud/formatClock";
import { resolveMeterTier } from "@/shared/lib/hud/resolveMeterTier";
import { HudPreviewProps } from "./HudPreview.types";

const MAX_PREVIEW_MINUTES = 480;
const DEFAULT_PREVIEW_MINUTES = 120;

export const HudPreview: React.FC<HudPreviewProps> = ({ hints }) => {
  const [minutes, setMinutes] = useState(DEFAULT_PREVIEW_MINUTES);
  const [values, setValues] = useState<Record<string, number>>({});
  const { clock, meters, tier } = hints;
  if (!clock && meters.length === 0 && !tier) return null;

  const meterProps = meters.map(({ path, hint }) => {
    const value = values[path] ?? hint.clamp_max;
    return {
      label: hint.label,
      value,
      clampMin: hint.clamp_min,
      clampMax: hint.clamp_max,
      tierName: resolveMeterTier(hint.tiers, value),
      shouldAnimate: false,
    };
  });

  return (
    <section aria-label="HUD preview" className="space-y-3">
      <h2 className="text-sm font-semibold text-content">Preview</h2>
      {clock && (
        <div className="space-y-1">
          <label className="block text-xs text-content-muted">
            Minutes into the shift: {minutes}
            <input
              type="range"
              aria-label="Preview minutes"
              min={0}
              max={MAX_PREVIEW_MINUTES}
              value={minutes}
              onChange={(event) => setMinutes(Number(event.target.value))}
              className="block w-full"
            />
          </label>
          <ShiftClockBadge
            label={clock.hint.label}
            time={formatClock(minutes, clock.hint.start, clock.hint.format)}
          />
        </div>
      )}
      {meters.map(({ path, hint }) => (
        <label key={path} className="block text-xs text-content-muted">
          {`Preview ${hint.label}: ${values[path] ?? hint.clamp_max}`}
          <input
            type="range"
            aria-label={`Preview ${hint.label}`}
            min={hint.clamp_min}
            max={hint.clamp_max}
            value={values[path] ?? hint.clamp_max}
            onChange={(event) =>
              setValues({ ...values, [path]: Number(event.target.value) })
            }
            className="block w-full"
          />
        </label>
      ))}
      <StatusHud
        meters={meterProps}
        tier={
          tier
            ? { label: tier.hint.label, options: tier.options, value: tier.options[0] ?? "" }
            : null
        }
      />
    </section>
  );
};

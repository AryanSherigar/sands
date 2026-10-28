import React from "react";
import { MeterBar } from "./MeterBar";
import { StatusHudProps } from "./StatusHud.types";
import { TierPips } from "./TierPips";

export const StatusHud: React.FC<StatusHudProps> = ({ meters, tier }) => (
  <div
    role="group"
    aria-label="Status"
    className="flex flex-wrap items-center gap-x-5 gap-y-1"
  >
    {meters.map((meter) => (
      <MeterBar key={meter.label} {...meter} />
    ))}
    {tier ? <TierPips {...tier} /> : null}
  </div>
);

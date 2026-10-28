import React from "react";

interface HeroCoverProps {
  coverImageUrl: string | null;
}

export const HeroCover: React.FC<HeroCoverProps> = ({ coverImageUrl }) => (
  <div className="relative aspect-21/9 max-h-[520px] w-full overflow-hidden lg:absolute lg:inset-0 lg:aspect-auto lg:max-h-none">
    {coverImageUrl ? (
      <img
        src={coverImageUrl}
        alt=""
        className="h-full w-full object-cover animate-fade-in"
      />
    ) : (
      <div
        aria-hidden="true"
        className="h-full w-full bg-linear-to-br from-accent/25 via-surface-inset to-surface-inset"
      />
    )}
    <div
      aria-hidden="true"
      className="absolute inset-0 hidden bg-linear-to-t from-surface via-surface/80 to-transparent lg:block"
    />
    <div
      aria-hidden="true"
      className="absolute inset-0 hidden bg-linear-to-r from-surface via-surface/60 to-transparent lg:block"
    />
  </div>
);

import React from "react";
import { ChromaticImage } from "@/shared/components/ui/aceternity/chromatic-image";

const LOGIN_HERO_SRC = "/images/login-hero.webp";

export const LoginHero: React.FC = () => {
  return (
    <ChromaticImage
      src={LOGIN_HERO_SRC}
      alt="A lone traveler standing before a colossal moss-draped ancient stone gateway with glowing runes"
      tilt={0}
      zoom={0.12}
      displacement={0.03}
      chromaticShift={0.006}
      className="h-full w-full filter-[contrast(0.95)_saturate(0.85)]"
    >
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-surface lg:bg-gradient-to-r lg:from-surface lg:via-surface/40 lg:to-transparent lg:w-2/5"
      />
    </ChromaticImage>
  );
};

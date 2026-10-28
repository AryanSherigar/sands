import React from "react";
import { ChromaticImage } from "@/shared/components/ui/aceternity/chromatic-image";

const LOGIN_HERO_SRC = "/images/login-hero.webp";
const SURFACE_SUNKEN_HEX = "#07080b";

export const LoginHero: React.FC = () => {
  return (
    <ChromaticImage
      src={LOGIN_HERO_SRC}
      alt="A person standing beneath a red light"
      backgroundColor={SURFACE_SUNKEN_HEX}
      tilt={0}
      zoom={0.12}
      displacement={0.03}
      chromaticShift={0.006}
      className="h-full w-full filter-[contrast(0.95)_saturate(0.85)]"
    >
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 bg-[linear-gradient(to_bottom,rgba(17,17,19,0)_60%,rgba(17,17,19,1)_100%)] lg:bg-[linear-gradient(to_right,rgba(17,17,19,1)_0%,rgba(17,17,19,0)_38%)]"
      />
    </ChromaticImage>
  );
};

import React from "react";
import { PRIVACY_PATH, TERMS_PATH } from "@/shared/constants/sign-in-triggers";

const LINK_CLASSES = "underline hover:text-content";

export const LegalLine: React.FC = () => (
  <p className="text-xs text-content-faint">
    By continuing you agree to the{" "}
    <a
      href={TERMS_PATH}
      target="_blank"
      rel="noopener noreferrer"
      className={LINK_CLASSES}
    >
      Terms
    </a>{" "}
    and{" "}
    <a
      href={PRIVACY_PATH}
      target="_blank"
      rel="noopener noreferrer"
      className={LINK_CLASSES}
    >
      Privacy Policy
    </a>
    .
  </p>
);

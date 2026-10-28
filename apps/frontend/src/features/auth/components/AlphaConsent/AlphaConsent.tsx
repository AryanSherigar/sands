import React from "react";
import { useAlphaConfig } from "@/shared/hooks/useAlphaConfig";
import {
  CONSENT_ACCEPTANCE_LINE,
  getAlphaConsentCopy,
} from "../../constants/alpha-consent";

const SIGNUP_CLOSED_NOTICE =
  "New sign-ups are closed right now. Existing testers can still sign in.";

export const AlphaConsent: React.FC = () => {
  const { data: config } = useAlphaConfig();
  if (!config?.is_alpha_mode) return null;
  const copy = getAlphaConsentCopy(config.consent_version);

  return (
    <section className="flex flex-col gap-2 rounded-md border border-border-subtle bg-surface-sunken px-4 py-3 text-xs text-content-muted">
      <h2 className="font-sans text-sm font-medium text-content">
        {copy.title}
      </h2>
      {copy.paragraphs.map((paragraph) => (
        <p key={paragraph}>{paragraph}</p>
      ))}
      {!config.is_signup_enabled && (
        <p role="status" className="font-medium text-content">
          {SIGNUP_CLOSED_NOTICE}
        </p>
      )}
      <p className="text-content-faint">{CONSENT_ACCEPTANCE_LINE}</p>
    </section>
  );
};

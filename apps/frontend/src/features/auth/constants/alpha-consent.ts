export interface AlphaConsentCopy {
  title: string;
  paragraphs: readonly string[];
}

export const LATEST_ALPHA_CONSENT_VERSION = "alpha-1";

// NOTE: Keyed by the server's alpha_consent_version. Changing any text here
// must bump ALPHA_CONSENT_VERSION on Core API so testers re-consent.
export const ALPHA_CONSENT_COPY: Readonly<Record<string, AlphaConsentCopy>> = {
  "alpha-1": {
    title: "Before you join the alpha",
    paragraphs: [
      "This is a closed test of an AI-narrated horror game. By continuing you agree to take part.",
      "We store your Google display name and account ID (not your email), the actions you type, the story the narrator writes, and what happens in the game, so we can fix problems and improve it.",
      "Your actions and the story so far are processed by Google's Gemini models to write each turn.",
      "We delete alpha data 90 days after the last test wave. You can delete your account at any time in Settings, and your data goes with it.",
    ],
  },
};

export const CONSENT_ACCEPTANCE_LINE =
  "Continuing with Google means you accept this.";

export function getAlphaConsentCopy(version: string | null): AlphaConsentCopy {
  const copy = version ? ALPHA_CONSENT_COPY[version] : undefined;
  return copy ?? ALPHA_CONSENT_COPY[LATEST_ALPHA_CONSENT_VERSION];
}

export interface AlphaConfig {
  is_alpha_mode: boolean;
  is_signup_enabled: boolean;
  consent_version: string | null;
  scenario_id: string | null;
  tension_prompt_every_turns: number | null;
}

export interface AlphaConsentStatus {
  alpha_consent_is_current: boolean;
}

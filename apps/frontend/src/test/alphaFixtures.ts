import { http, HttpResponse } from "msw";
import type { AlphaConfig } from "@/shared/types/alpha.types";

export const ALPHA_CONSENT_VERSION = "alpha-1";

export const NON_ALPHA_CONFIG: AlphaConfig = {
  is_alpha_mode: false,
  is_signup_enabled: true,
  consent_version: null,
  scenario_id: null,
  tension_prompt_every_turns: null,
};

export const ALPHA_CONFIG: AlphaConfig = {
  is_alpha_mode: true,
  is_signup_enabled: true,
  consent_version: ALPHA_CONSENT_VERSION,
  scenario_id: "11111111-1111-1111-1111-111111111111",
  tension_prompt_every_turns: 15,
};

export const alphaConfigHandler = (config: AlphaConfig) =>
  http.get("*/v1/alpha/config", () => HttpResponse.json(config));

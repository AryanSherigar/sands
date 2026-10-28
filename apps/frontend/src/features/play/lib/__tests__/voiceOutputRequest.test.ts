import { beforeEach, describe, expect, it } from "vitest";
import { queryClient } from "@/shared/lib/query-client";
import { ALPHA_CONFIG_QUERY_KEY } from "@/shared/hooks/useAlphaConfig";
import { VOICE_OUTPUT_PREFERENCE_QUERY_KEY } from "@/shared/hooks/useVoiceOutputPreference";
import { ALPHA_CONFIG, NON_ALPHA_CONFIG } from "@/test/alphaFixtures";
import { isVoiceOutputRequested } from "../voiceOutputRequest";

describe("isVoiceOutputRequested", () => {
  beforeEach(() => {
    queryClient.clear();
  });

  it("is false before the preference has loaded", () => {
    expect(isVoiceOutputRequested()).toBe(false);
  });

  it("follows the cached preference when alpha mode is off", () => {
    queryClient.setQueryData(VOICE_OUTPUT_PREFERENCE_QUERY_KEY, {
      voice_output_enabled: true,
    });
    queryClient.setQueryData(ALPHA_CONFIG_QUERY_KEY, NON_ALPHA_CONFIG);
    expect(isVoiceOutputRequested()).toBe(true);
  });

  it("is false in alpha mode even when the stored preference is on", () => {
    queryClient.setQueryData(VOICE_OUTPUT_PREFERENCE_QUERY_KEY, {
      voice_output_enabled: true,
    });
    queryClient.setQueryData(ALPHA_CONFIG_QUERY_KEY, ALPHA_CONFIG);
    expect(isVoiceOutputRequested()).toBe(false);
  });
});

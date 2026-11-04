import { beforeEach, describe, expect, it } from "vitest";
import { queryClient } from "@/shared/lib/query-client";
import { VOICE_OUTPUT_PREFERENCE_QUERY_KEY } from "@/shared/hooks/useVoiceOutputPreference";
import { isVoiceOutputRequested } from "../voiceOutputRequest";

describe("isVoiceOutputRequested", () => {
  beforeEach(() => {
    queryClient.clear();
  });

  it("is false before the preference has loaded", () => {
    expect(isVoiceOutputRequested()).toBe(false);
  });

  it("follows the cached preference", () => {
    queryClient.setQueryData(VOICE_OUTPUT_PREFERENCE_QUERY_KEY, {
      voice_output_enabled: true,
    });
    expect(isVoiceOutputRequested()).toBe(true);
  });
});

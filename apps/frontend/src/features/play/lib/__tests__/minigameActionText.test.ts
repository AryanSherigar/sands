import { describe, expect, it } from "vitest";
import {
  DEFAULT_COMPOSURE_CONFIG,
  type MinigameEventPayload,
} from "@/shared/types/minigame.types";
import { minigameActionText } from "../minigameActionText";

const BASE_MINIGAME: MinigameEventPayload = {
  minigame_id: "mg-1",
  minigame_type: "rhythm_composure",
  label: "The Hum",
  timeout_seconds: 30,
};

const HUM: MinigameEventPayload = {
  ...BASE_MINIGAME,
  composure_config: {
    ...DEFAULT_COMPOSURE_CONFIG,
    texts: {
      ...DEFAULT_COMPOSURE_CONFIG.texts,
      win_text: "You hum until the chime.",
      lose_text: "You answer the voice.",
    },
  },
};

describe("minigameActionText", () => {
  it("uses the composure win text", () => {
    expect(minigameActionText(HUM, "win")).toBe("You hum until the chime.");
  });

  it("uses the lose text for a loss and a timeout", () => {
    expect(minigameActionText(HUM, "lose")).toBe("You answer the voice.");
    expect(minigameActionText(HUM, "timeout")).toBe("You answer the voice.");
  });

  it("falls back when no config text exists", () => {
    expect(minigameActionText(BASE_MINIGAME, "win")).toBe("You finish.");
    expect(minigameActionText(BASE_MINIGAME, "timeout")).toBe("You stop.");
  });
});

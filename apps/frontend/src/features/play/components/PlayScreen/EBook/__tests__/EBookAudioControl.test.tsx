import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { usePlayStore } from "../../../../stores/play.store";
import { EBookAudioControl } from "../EBookAudioControl";

const tension = vi.hoisted(() => ({
  reading: null as null | {
    value: string;
    index: number;
    count: number;
    moodMap: Record<string, string>;
  },
}));

vi.mock("../../../../hooks/useTensionTier", () => ({
  useTensionTier: () => tension.reading,
}));

describe("EBookAudioControl label", () => {
  beforeEach(() => {
    usePlayStore.setState({ active_mood: "combat", is_audio_muted: false });
  });

  it("names the tension tier instead of the mood slot", () => {
    tension.reading = {
      value: "breaking",
      index: 3,
      count: 4,
      moodMap: { breaking: "combat" },
    };
    render(<EBookAudioControl />);
    expect(screen.getByText("Breaking")).toBeInTheDocument();
    expect(screen.queryByText("Combat")).not.toBeInTheDocument();
  });

  it("names the mood when the scenario has no tension tier", () => {
    tension.reading = null;
    render(<EBookAudioControl />);
    expect(screen.getByText("Combat")).toBeInTheDocument();
  });
});

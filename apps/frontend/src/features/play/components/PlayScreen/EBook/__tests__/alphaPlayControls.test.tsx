import { render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { server } from "@/test/msw/server";
import { ALPHA_CONFIG, NON_ALPHA_CONFIG } from "@/test/alphaFixtures";
import { createQueryWrapper } from "@/test/queryWrapper";
import type { AlphaConfig } from "@/shared/types/alpha.types";
import { usePlayStore } from "../../../../stores/play.store";
import type { PlaythroughData } from "../../../../types/play.types";
import { ChronicleRecapModal } from "../ChronicleRecapModal";
import { EBookActionDrawer } from "../EBookActionDrawer";
import { EBookNarrationVoiceControl } from "../EBookNarrationVoiceControl";

vi.mock("../../../../hooks/useVoiceInput", () => ({
  useVoiceInput: () => ({
    status: "idle",
    isSupported: true,
    errorMessage: null,
    startRecording: vi.fn(),
    stopRecording: vi.fn(),
    cancelRecording: vi.fn(),
  }),
}));

const renderWith = (config: AlphaConfig, ui: React.ReactElement): void => {
  server.use(
    http.get("*/v1/users/me", () =>
      HttpResponse.json({ voice_output_enabled: false }),
    ),
  );
  const Wrapper = createQueryWrapper(config);
  render(
    <Wrapper>
      <MemoryRouter>{ui}</MemoryRouter>
    </Wrapper>,
  );
};

describe("EBookNarrationVoiceControl", () => {
  it("offers the voice toggle when alpha mode is off", () => {
    renderWith(NON_ALPHA_CONFIG, <EBookNarrationVoiceControl />);
    expect(screen.getByRole("button", { name: /voice narration/i })).toBeInTheDocument();
  });

  it("is hidden in alpha mode", () => {
    renderWith(ALPHA_CONFIG, <EBookNarrationVoiceControl />);
    expect(screen.queryByRole("button", { name: /voice narration/i })).toBeNull();
  });
});

describe("EBookActionDrawer", () => {
  const drawer = (
    <EBookActionDrawer onContinue={vi.fn()} onRetry={vi.fn()} canRetry={false} 
      onSubmit={vi.fn()}
      isNarrating={false}
      playthroughId="p1"
    />
  );

  it("offers the microphone when alpha mode is off", () => {
    renderWith(NON_ALPHA_CONFIG, drawer);
    expect(screen.getByTitle("Speak your action")).toBeInTheDocument();
  });

  it("hides the microphone in alpha mode", () => {
    renderWith(ALPHA_CONFIG, drawer);
    expect(screen.queryByTitle("Speak your action")).toBeNull();
    expect(screen.getByRole("button", { name: "Do" })).toBeInTheDocument();
  });
});

describe("ChronicleRecapModal", () => {
  beforeEach(() => {
    usePlayStore.setState({
      playthrough: {
        scenario_title: "Night Desk",
        character_name: "Rowan",
        opening_premise: "The lobby is empty.",
        turns: [],
      } as unknown as PlaythroughData,
    });
  });

  it("offers a share link when alpha mode is off", () => {
    renderWith(NON_ALPHA_CONFIG, <ChronicleRecapModal isOpen onClose={vi.fn()} />);
    expect(screen.getByRole("button", { name: /copy share link/i })).toBeInTheDocument();
  });

  it("offers no share link in alpha mode", () => {
    renderWith(ALPHA_CONFIG, <ChronicleRecapModal isOpen onClose={vi.fn()} />);
    expect(screen.queryByRole("button", { name: /copy share link/i })).toBeNull();
    expect(screen.getByRole("button", { name: /keep reading/i })).toBeInTheDocument();
  });
});

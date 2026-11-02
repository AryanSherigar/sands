import { render, screen } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { NegotiationRulerDossier } from "../NegotiationRulerDossier";

type MockAvatarHandle = { avatar: { setSpeaking: typeof mockSetSpeaking }; setVoiceLevel: typeof mockSetVoiceLevel };
type MockAvatarProps = { src: string; expression: string; label: string; style?: React.CSSProperties; onError?: (error: Error) => void };

const mockSetSpeaking = vi.fn();
const mockSetVoiceLevel = vi.fn();

vi.mock("mesh-avatar-react", () => ({
  MeshAvatar: React.forwardRef<MockAvatarHandle, MockAvatarProps>(
    ({ src, expression, label, style }, ref) => {
      React.useImperativeHandle(ref, () => ({
        avatar: {
          setSpeaking: mockSetSpeaking,
        },
        setVoiceLevel: mockSetVoiceLevel,
      }));
      return (
        <div
          data-testid="mesh-avatar"
          data-src={src}
          data-expression={expression}
          aria-label={label}
          style={style}
        />
      );
    }
  ),
}));

describe("NegotiationRulerDossier", () => {
  const originalWebGL2 = window.WebGL2RenderingContext;
  const originalGetContext = HTMLCanvasElement.prototype.getContext;

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    window.WebGL2RenderingContext = originalWebGL2;
    HTMLCanvasElement.prototype.getContext = originalGetContext;
  });

  function enableMockWebGL2() {
    window.WebGL2RenderingContext = class WebGL2RenderingContext {} as unknown as typeof WebGL2RenderingContext;
    HTMLCanvasElement.prototype.getContext = ((contextId: string) =>
      contextId === "webgl2" ? ({} as WebGL2RenderingContext) : null
    ) as typeof HTMLCanvasElement.prototype.getContext;
  }

  function disableWebGL2() {
    // @ts-expect-error simulating missing WebGL2 in test environment
    delete window.WebGL2RenderingContext;
  }

  it("renders rival info, mood tag, and player royal status deck", () => {
    render(
      <NegotiationRulerDossier
        leaderName="Queen Mira"
        factionName="House Valdren"
        traitIds={["cautious", "proud"]}
        isAtWar={true}
        playerLeaderName="King Aldric"
        playerFactionName="Western Reach"
        playerGold={420}
        playerLevies={1200}
      />
    );

    expect(screen.getByText("Queen Mira")).toBeInTheDocument();
    expect(screen.getByText("Sovereign of House Valdren")).toBeInTheDocument();
    expect(screen.getByText("Guarded — Distrustful")).toBeInTheDocument();
    expect(screen.getByText("King Aldric")).toBeInTheDocument();
    expect(screen.getByText("Western Reach")).toBeInTheDocument();
    expect(screen.getByText("420 Gold")).toBeInTheDocument();
    expect(screen.getByText("1,200 Levies")).toBeInTheDocument();
    // Default fallback portrait/crest image
    expect(
      screen.getByRole("img", { name: "Queen Mira of House Valdren" })
    ).toBeInTheDocument();
  });

  it("renders static fallback image when avatarUrl is absent", () => {
    disableWebGL2();
    render(
      <NegotiationRulerDossier
        leaderName="Queen Mira"
        factionName="Dunmere"
        portraitUrl="https://example.com/mira.png"
        playerLeaderName="King Alden IV"
        playerFactionName="Valenreach"
        playerGold={340}
        playerLevies={14200}
      />
    );

    const img = screen.getByRole("img", { name: "Queen Mira of Dunmere" });
    expect(img).toBeInTheDocument();
    expect(img).toHaveAttribute("src", "https://example.com/mira.png");
  });

  it("renders MeshAvatar when avatarUrl is provided and WebGL2 is supported", () => {
    enableMockWebGL2();
    render(
      <NegotiationRulerDossier
        leaderName="Queen Mira"
        factionName="Dunmere"
        avatarUrl="/avatars/mira.mavatar"
        portraitUrl="https://example.com/mira.png"
        expression="angry"
        isSpeaking={true}
        playerLeaderName="King Alden IV"
        playerFactionName="Valenreach"
        playerGold={340}
        playerLevies={14200}
      />
    );

    const meshAvatar = screen.getByTestId("mesh-avatar");
    expect(meshAvatar).toBeInTheDocument();
    expect(meshAvatar).toHaveAttribute("data-src", "/avatars/mira.mavatar");
    expect(meshAvatar).toHaveAttribute("data-expression", "angry");
    expect(meshAvatar).toHaveAttribute("aria-label", "Queen Mira of Dunmere");
    expect(mockSetSpeaking).toHaveBeenCalledWith(true);
    expect(mockSetVoiceLevel).toHaveBeenCalledWith(0.65);
  });

  it("updates emotion expression and speech state on prop changes", () => {
    enableMockWebGL2();
    const { rerender } = render(
      <NegotiationRulerDossier
        leaderName="Queen Mira"
        factionName="Dunmere"
        avatarUrl="/avatars/mira.mavatar"
        expression="halfLidded"
        isSpeaking={false}
        playerLeaderName="King Alden IV"
        playerFactionName="Valenreach"
        playerGold={340}
        playerLevies={14200}
      />
    );

    const meshAvatar = screen.getByTestId("mesh-avatar");
    expect(meshAvatar).toHaveAttribute("data-expression", "halfLidded");
    expect(mockSetSpeaking).toHaveBeenCalledWith(false);
    expect(mockSetVoiceLevel).toHaveBeenCalledWith(0);

    rerender(
      <NegotiationRulerDossier
        leaderName="Queen Mira"
        factionName="Dunmere"
        avatarUrl="/avatars/mira.mavatar"
        expression="smile"
        isSpeaking={true}
        playerLeaderName="King Alden IV"
        playerFactionName="Valenreach"
        playerGold={340}
        playerLevies={14200}
      />
    );

    expect(meshAvatar).toHaveAttribute("data-expression", "smile");
    expect(mockSetSpeaking).toHaveBeenLastCalledWith(true);
    expect(mockSetVoiceLevel).toHaveBeenLastCalledWith(0.65);
  });
});

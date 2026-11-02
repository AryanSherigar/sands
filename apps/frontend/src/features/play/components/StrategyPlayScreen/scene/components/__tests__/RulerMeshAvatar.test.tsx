import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { RulerMeshAvatar } from "../RulerMeshAvatar";
import { useReaderPreferencesStore } from "@/shared/stores/readerPreferences.store";

type MockAvatarHandle = { avatar: { setSpeaking: typeof mockSetSpeaking }; setVoiceLevel: typeof mockSetVoiceLevel };
type MockAvatarProps = { src: string; expression: string; label: string; style?: React.CSSProperties; onError?: (error: Error) => void };

const mockSetSpeaking = vi.fn();
const mockSetVoiceLevel = vi.fn();

vi.mock("mesh-avatar-react", () => ({
  MeshAvatar: React.forwardRef<MockAvatarHandle, MockAvatarProps>(
    ({ src, expression, label, onError, style }, ref) => {
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
        >
          <button
            data-testid="trigger-error"
            onClick={() => onError?.(new Error("Avatar load failed"))}
          >
            Trigger Error
          </button>
        </div>
      );
    }
  ),
}));

describe("RulerMeshAvatar", () => {
  const originalWebGL2 = window.WebGL2RenderingContext;
  const originalGetContext = HTMLCanvasElement.prototype.getContext;

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    useReaderPreferencesStore.setState({ reduceSensoryEffects: false });
    window.WebGL2RenderingContext = originalWebGL2;
    HTMLCanvasElement.prototype.getContext = originalGetContext;
  });

  it("uses the static portrait when reduced sensory effects are enabled", () => {
    enableMockWebGL2();
    useReaderPreferencesStore.setState({ reduceSensoryEffects: true });
    render(<RulerMeshAvatar avatarUrl="/mira.mavatar" portraitUrl="/mira.png" fallbackCrest="/crest.png" leaderName="Mira" factionName="Dunmere" />);
    expect(screen.getByRole("img", { name: "Mira of Dunmere" })).toHaveAttribute("src", "/mira.png");
    expect(screen.queryByTestId("mesh-avatar")).not.toBeInTheDocument();
  });

  it("uses the matching generated still image and falls back if unavailable", () => {
    useReaderPreferencesStore.setState({ reduceSensoryEffects: true });
    const id = "e44c60fb-620d-4388-bf15-126930454ad9";
    render(<RulerMeshAvatar avatarUrl={`https://assets.example/avatars/${id}.mavatar`} fallbackCrest="/crest.png" leaderName="Mira" factionName="Dunmere" />);
    const portrait = screen.getByRole("img", { name: "Mira of Dunmere" });
    expect(portrait).toHaveAttribute("src", `https://assets.example/avatars/${id}.png`);
    fireEvent.error(portrait);
    expect(portrait).toHaveAttribute("src", "/crest.png");
  });

  function enableMockWebGL2() {
    window.WebGL2RenderingContext = class WebGL2RenderingContext {} as unknown as typeof WebGL2RenderingContext;
    HTMLCanvasElement.prototype.getContext = ((contextId: string) =>
      contextId === "webgl2" ? ({} as WebGL2RenderingContext) : null
    ) as typeof HTMLCanvasElement.prototype.getContext;
  }

  function disableWebGL2() {
    // @ts-expect-error simulating missing WebGL2 in environment
    delete window.WebGL2RenderingContext;
  }

  it("renders 2D fallback image when avatarUrl is null", () => {
    render(
      <RulerMeshAvatar
        avatarUrl={null}
        portraitUrl="https://example.com/portrait.png"
        fallbackCrest="data:image/svg+xml;utf8,<svg></svg>"
        leaderName="Queen Mira"
        factionName="Dunmere"
      />
    );
    const img = screen.getByRole("img", { name: "Queen Mira of Dunmere" });
    expect(img).toBeInTheDocument();
    expect(img).toHaveAttribute("src", "https://example.com/portrait.png");
  });

  it("renders fallback crest when both avatarUrl and portraitUrl are absent", () => {
    render(
      <RulerMeshAvatar
        avatarUrl={null}
        portraitUrl={undefined}
        fallbackCrest="data:image/svg+xml;utf8,<svg test></svg>"
        leaderName="Unknown Leader"
        factionName="Dunmere"
      />
    );
    const img = screen.getByRole("img", { name: "Unknown Leader of Dunmere" });
    expect(img).toBeInTheDocument();
    expect(img).toHaveAttribute(
      "src",
      "data:image/svg+xml;utf8,<svg test></svg>"
    );
  });

  it("renders 2D fallback when WebGL2 is not available even if avatarUrl is provided", () => {
    disableWebGL2();
    render(
      <RulerMeshAvatar
        avatarUrl="https://example.com/mira.mavatar"
        portraitUrl="https://example.com/portrait.png"
        fallbackCrest="data:image/svg+xml;utf8,<svg></svg>"
        leaderName="Queen Mira"
        factionName="Dunmere"
      />
    );
    expect(screen.queryByTestId("mesh-avatar")).not.toBeInTheDocument();
    const img = screen.getByRole("img", { name: "Queen Mira of Dunmere" });
    expect(img).toBeInTheDocument();
    expect(img).toHaveAttribute("src", "https://example.com/portrait.png");
  });

  it("renders MeshAvatar and forwards expression when WebGL2 is available", () => {
    enableMockWebGL2();
    render(
      <RulerMeshAvatar
        avatarUrl="https://example.com/mira.mavatar"
        portraitUrl="https://example.com/portrait.png"
        fallbackCrest="data:image/svg+xml;utf8,<svg></svg>"
        leaderName="Queen Mira"
        factionName="Dunmere"
        expression="smile"
      />
    );

    const meshAvatar = screen.getByTestId("mesh-avatar");
    expect(meshAvatar).toBeInTheDocument();
    expect(meshAvatar).toHaveAttribute(
      "data-src",
      "https://example.com/mira.mavatar"
    );
    expect(meshAvatar).toHaveAttribute("data-expression", "smile");
    expect(meshAvatar).toHaveAttribute("aria-label", "Queen Mira of Dunmere");
  });

  it("falls back gracefully when MeshAvatar triggers onError", () => {
    enableMockWebGL2();
    render(
      <RulerMeshAvatar
        avatarUrl="https://example.com/corrupt.mavatar"
        portraitUrl="https://example.com/portrait.png"
        fallbackCrest="data:image/svg+xml;utf8,<svg></svg>"
        leaderName="Queen Mira"
        factionName="Dunmere"
      />
    );

    expect(screen.getByTestId("mesh-avatar")).toBeInTheDocument();

    // Trigger error
    fireEvent.click(screen.getByTestId("trigger-error"));

    expect(screen.queryByTestId("mesh-avatar")).not.toBeInTheDocument();
    const img = screen.getByRole("img", { name: "Queen Mira of Dunmere" });
    expect(img).toBeInTheDocument();
    expect(img).toHaveAttribute("src", "https://example.com/portrait.png");
  });

  it("forwards speaking states: speaks with level 0.65 when isSpeaking is true, resets to 0 when false", () => {
    enableMockWebGL2();
    const { rerender } = render(
      <RulerMeshAvatar
        avatarUrl="https://example.com/mira.mavatar"
        portraitUrl="https://example.com/portrait.png"
        fallbackCrest="data:image/svg+xml;utf8,<svg></svg>"
        leaderName="Queen Mira"
        factionName="Dunmere"
        isSpeaking={false}
      />
    );

    expect(mockSetSpeaking).toHaveBeenCalledWith(false);
    expect(mockSetVoiceLevel).toHaveBeenCalledWith(0);

    // Update isSpeaking to true
    rerender(
      <RulerMeshAvatar
        avatarUrl="https://example.com/mira.mavatar"
        portraitUrl="https://example.com/portrait.png"
        fallbackCrest="data:image/svg+xml;utf8,<svg></svg>"
        leaderName="Queen Mira"
        factionName="Dunmere"
        isSpeaking={true}
      />
    );

    expect(mockSetSpeaking).toHaveBeenCalledWith(true);
    expect(mockSetVoiceLevel).toHaveBeenCalledWith(0.65);

    // Return to false
    rerender(
      <RulerMeshAvatar
        avatarUrl="https://example.com/mira.mavatar"
        portraitUrl="https://example.com/portrait.png"
        fallbackCrest="data:image/svg+xml;utf8,<svg></svg>"
        leaderName="Queen Mira"
        factionName="Dunmere"
        isSpeaking={false}
      />
    );

    expect(mockSetSpeaking).toHaveBeenLastCalledWith(false);
    expect(mockSetVoiceLevel).toHaveBeenLastCalledWith(0);
  });
});

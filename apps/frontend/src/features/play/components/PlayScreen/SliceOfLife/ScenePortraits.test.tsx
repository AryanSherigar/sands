import { act, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ScenePortraits } from "./ScenePortraits";

const speaker = vi.hoisted(() => ({ listener: (_name: string | null) => {} }));
vi.mock("@/shared/lib/audio/narration-playback", () => ({
  narrationPlayback: { onSpeakerChange: (listener: typeof speaker.listener) => { speaker.listener = listener; return () => {}; } },
}));
vi.mock("@/shared/components/AnimatedPortrait/AnimatedPortrait", () => ({
  AnimatedPortrait: ({ label, isSpeaking }: { label: string; isSpeaking: boolean }) => <div role="img" aria-label={label} data-speaking={String(isSpeaking)} />,
}));

describe("scene portraits", () => {
  it("shows only server-projected characters still explicitly present", () => {
    render(<ScenePortraits portraits={[{ entity_id: "a", name: "Asha", avatar_url: "a" }, { entity_id: "b", name: "Bao", avatar_url: "b" }]} presentIds={["a"]} />);
    expect(screen.getByRole("img", { name: "Asha" })).toBeInTheDocument();
    expect(screen.queryByRole("img", { name: "Bao" })).not.toBeInTheDocument();
  });

  it("renders nothing without explicit scene presence", () => {
    const { container } = render(<ScenePortraits portraits={[{ entity_id: "a", name: "Asha", avatar_url: "a" }]} presentIds={undefined} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("animates only the uniquely matching current speaker", () => {
    render(<ScenePortraits portraits={[{ entity_id: "a", name: "Asha", avatar_url: "a" }, { entity_id: "b", name: "Bao", avatar_url: "b" }]} presentIds={["a", "b"]} />);
    act(() => speaker.listener("Asha"));
    expect(screen.getByRole("img", { name: "Asha" })).toHaveAttribute("data-speaking", "true");
    expect(screen.getByRole("img", { name: "Bao" })).toHaveAttribute("data-speaking", "false");
    act(() => speaker.listener(null));
    expect(screen.getByRole("img", { name: "Asha" })).toHaveAttribute("data-speaking", "false");
  });
});

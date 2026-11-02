import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { buildLetterPackage } from "../../../../lib/letter-package";
import type { SceneViewResponse } from "../../../../types/scene.types";
import { StrategyLetterDialog } from "../StrategyLetterDialog";

const SENDER = "Mira of Ashford";
const INCOMING = "Valdren, the river fords are watched.\n\nKeep your riders home.";
const SCRIBE_DRAFT = "Mira, our bailiffs will walk the line with yours in spring.";

const VIEW: SceneViewResponse = {
  scene_id: "scene-live",
  scene_type: "letter",
  status: "opened",
  turn: 6,
  initiator: "ai",
  is_declinable: true,
  situation: { summary: "Mira writes.", facts: [{ label: "Topic", value: "warning" }] },
  participants: [
    { participant_id: "mira", kind: "leader", name: SENDER, trait_ids: [] },
  ],
  transcript: [{ sequence: 1, player_text: "", leader_text: INCOMING }],
  exchanges_remaining: 1,
};

const pkg = buildLetterPackage(VIEW, INCOMING);

function renderDialog(overrides: Partial<React.ComponentProps<typeof StrategyLetterDialog>> = {}) {
  const props = {
    isOpen: true,
    pkg,
    onSeal: vi.fn().mockResolvedValue(true),
    onClose: vi.fn(),
    onRequestScribeDraft: vi.fn().mockResolvedValue(SCRIBE_DRAFT),
    ...overrides,
  };
  render(<StrategyLetterDialog {...props} />);
  return props;
}

describe("StrategyLetterDialog with a real scene", () => {
  it("shows the stored letter and the real sender, not fixture text", () => {
    const { container } = render(<StrategyLetterDialog isOpen pkg={pkg} />);

    expect(screen.getByText("Valdren, the river fords are watched.")).toBeInTheDocument();
    expect(screen.getByText("Keep your riders home.")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: `Reply to ${SENDER}` })).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(/Dunmere|Queen Mira/);
    expect(container.querySelectorAll('img[src=""]')).toHaveLength(0);
  });

  it("asks the scribe with the typed instruction and shows the drafted prose", async () => {
    const props = renderDialog();
    fireEvent.click(screen.getByRole("button", { name: /Ask my scribe/i }));

    const hint = screen.getByPlaceholderText(/Draft hint:/i);
    fireEvent.change(hint, { target: { value: "Be firm about the fords" } });
    fireEvent.click(screen.getByRole("button", { name: /Rewrite/i }));

    await waitFor(() =>
      expect(props.onRequestScribeDraft).toHaveBeenCalledWith("Be firm about the fords", ""),
    );
    expect(await screen.findByText(SCRIBE_DRAFT)).toBeInTheDocument();
  });

  it("seals the drafted prose through onSeal and closes only after it succeeds", async () => {
    vi.useFakeTimers();
    const props = renderDialog();
    fireEvent.click(screen.getByRole("button", { name: /Ask my scribe/i }));
    fireEvent.change(screen.getByPlaceholderText(/Draft hint:/i), {
      target: { value: "Be firm" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Rewrite/i }));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });

    fireEvent.click(screen.getByRole("button", { name: /Seal and send/i }));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(300);
    });

    expect(props.onSeal).toHaveBeenCalledWith(
      expect.objectContaining({ sceneId: "scene-live", finalProse: SCRIBE_DRAFT }),
    );
    expect(props.onClose).toHaveBeenCalledTimes(1);
    vi.useRealTimers();
  });

  it("stays open with the draft when sealing fails", async () => {
    vi.useFakeTimers();
    const props = renderDialog({ onSeal: vi.fn().mockResolvedValue(false) });
    fireEvent.click(screen.getByRole("button", { name: /Write it myself/i }));
    const quill = screen.getAllByRole("textbox")[0];
    fireEvent.change(quill, { target: { value: "My own words." } });

    fireEvent.click(screen.getByRole("button", { name: /Seal and send/i }));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(300);
    });

    expect(props.onClose).not.toHaveBeenCalled();
    expect(screen.getByText(/not sent/i)).toBeInTheDocument();
    vi.useRealTimers();
  });

  it("tells the player when the scribe fails and keeps the draft", async () => {
    const props = renderDialog({
      onRequestScribeDraft: vi.fn().mockRejectedValue(new Error("down")),
    });
    fireEvent.click(screen.getByRole("button", { name: /Ask my scribe/i }));
    fireEvent.change(screen.getByPlaceholderText(/Draft hint:/i), {
      target: { value: "Firmer" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Rewrite/i }));

    expect(await screen.findByText(/scribe could not/i)).toBeInTheDocument();
    expect(props.onSeal).not.toHaveBeenCalled();
  });
});

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import { StrategyLetterDialog } from "../StrategyLetterDialog";
import { DEFAULT_LETTER_SCENARIO } from "../fixtures/defaultLetterScenario";

describe("StrategyLetterDialog integration", () => {
  it("renders nothing when isOpen is false", () => {
    render(
      <StrategyLetterDialog
        isOpen={false}
        pkg={DEFAULT_LETTER_SCENARIO}
      />
    );

    expect(screen.queryByText("Unfolded Courier Pouch")).toBeNull();
  });

  it("switches from pouch reading stage to scribe drafting stage and seals dispatch", async () => {
    vi.useFakeTimers();
    const onSeal = vi.fn();
    const onClose = vi.fn();

    render(
      <StrategyLetterDialog
        isOpen={true}
        pkg={DEFAULT_LETTER_SCENARIO}
        onSeal={onSeal}
        onClose={onClose}
      />
    );

    expect(screen.getByText("Unfolded Courier Pouch")).toBeInTheDocument();
    const scribeChoice = screen.getByRole("button", { name: /Ask my scribe/i });
    fireEvent.click(scribeChoice);

    expect(screen.getByText("Drafting Courier Missive")).toBeInTheDocument();
    const sealBtn = screen.getByRole("button", { name: /Seal and send/i });
    fireEvent.click(sealBtn);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(300);
    });

    expect(onSeal).toHaveBeenCalledTimes(1);
    expect(onClose).toHaveBeenCalledTimes(1);
    vi.useRealTimers();
  });

  it("handles setting aside the letter and triggering onClose", () => {
    const onClose = vi.fn();
    render(
      <StrategyLetterDialog
        isOpen={true}
        pkg={DEFAULT_LETTER_SCENARIO}
        onClose={onClose}
      />
    );

    const asideBtn = screen.getByRole("button", { name: /Set it aside/i });
    fireEvent.click(asideBtn);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("toggles ambient mute in canopy", () => {
    render(
      <StrategyLetterDialog
        isOpen={true}
        pkg={DEFAULT_LETTER_SCENARIO}
      />
    );

    const muteBtn = screen.getByRole("button", { name: /Toggle ambient study audio/i });
    expect(muteBtn).toBeInTheDocument();
    expect(screen.getByText("volume_up")).toBeInTheDocument();

    fireEvent.click(muteBtn);
    expect(screen.getByText("volume_off")).toBeInTheDocument();
  });

  it("lets the player decline to answer", () => {
    const onDecline = vi.fn();
    render(
      <StrategyLetterDialog isOpen pkg={DEFAULT_LETTER_SCENARIO} onDecline={onDecline} />
    );

    fireEvent.click(screen.getByRole("button", { name: /Decline to answer/i }));

    expect(onDecline).toHaveBeenCalledTimes(1);
  });
});

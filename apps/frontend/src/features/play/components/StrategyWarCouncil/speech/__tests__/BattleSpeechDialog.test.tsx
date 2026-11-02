import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { BattleSpeechDialog } from "../BattleSpeechDialog";

const base = { isSending: false, reception: null, errorMessage: null, onSpeak: vi.fn(), onSkip: vi.fn(), onFinish: vi.fn() };

describe("BattleSpeechDialog", () => {
  it("sends trimmed words, and cannot send nothing", () => {
    const onSpeak = vi.fn();
    render(<BattleSpeechDialog {...base} onSpeak={onSpeak} />);
    const send = screen.getByRole("button", { name: "Address the host" });

    expect(send).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Your words to the host"), { target: { value: "  Stand firm.  " } });
    fireEvent.click(send);

    expect(onSpeak).toHaveBeenCalledWith("Stand firm.");
  });

  it("lets the ruler say nothing, also on Escape", () => {
    const onSkip = vi.fn();
    render(<BattleSpeechDialog {...base} onSkip={onSkip} />);

    fireEvent.click(screen.getByRole("button", { name: "Say nothing" }));
    fireEvent.keyDown(document, { key: "Escape" });

    expect(onSkip).toHaveBeenCalledTimes(2);
  });

  it("shows the ranks' mood in words, never a number, then lets the player go on", () => {
    const onFinish = vi.fn();
    render(<BattleSpeechDialog {...base} reception="cold" onFinish={onFinish} />);

    expect(screen.getByRole("status")).toHaveTextContent("cold silence");
    expect(screen.queryByText(/%/)).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "To the field" }));
    expect(onFinish).toHaveBeenCalled();
  });

  it("adds the officer's line under the reception when one arrives", () => {
    render(<BattleSpeechDialog {...base} reception="stirred" reactionLine="A sergeant grips his spear harder." />);

    expect(screen.getByText("A sergeant grips his spear harder.")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("roar");
  });

  it("shows pending and error states", () => {
    const { rerender } = render(<BattleSpeechDialog {...base} isSending />);
    expect(screen.getByRole("button", { name: "The ranks listen…" })).toBeDisabled();

    rerender(<BattleSpeechDialog {...base} errorMessage="Try again." />);
    expect(screen.getByRole("alert")).toHaveTextContent("Try again.");
  });
});

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { LetterDraftingStage } from "../LetterDraftingStage";
import { DEFAULT_LETTER_SCENARIO } from "../../fixtures/defaultLetterScenario";

describe("LetterDraftingStage", () => {
  it("renders archival reference, active drafting canvas, and seal button", () => {
    const handleSeal = vi.fn();
    const handleRewrite = vi.fn();
    const handleDiscard = vi.fn();

    render(
      <LetterDraftingStage
        pkg={DEFAULT_LETTER_SCENARIO}
        activeDraft={DEFAULT_LETTER_SCENARIO.initialDraft}
        mode="scribe"
        canUndo={false}
        canRedo={false}
        isSealing={false}
        onRewrite={handleRewrite}
        onUpdateBody={vi.fn()}
        onUndo={vi.fn()}
        onRedo={vi.fn()}
        onDiscard={handleDiscard}
        onSealAndSend={handleSeal}
      />
    );

    expect(screen.getByText("Reference: Incoming Dispatch #8")).toBeInTheDocument();
    expect(screen.getByText("Brother Lucan")).toBeInTheDocument();
    expect(screen.getByText(/We can spare eighty cartloads/i)).toBeInTheDocument();

    const sealBtn = screen.getByRole("button", { name: /Seal and send/i });
    fireEvent.click(sealBtn);
    expect(handleSeal).toHaveBeenCalled();
  });

  it("handles rewrite submission from actions deck", () => {
    const handleRewrite = vi.fn();

    render(
      <LetterDraftingStage
        pkg={DEFAULT_LETTER_SCENARIO}
        activeDraft={DEFAULT_LETTER_SCENARIO.initialDraft}
        mode="scribe"
        canUndo={true}
        canRedo={true}
        isSealing={false}
        onRewrite={handleRewrite}
        onUpdateBody={vi.fn()}
        onUndo={vi.fn()}
        onRedo={vi.fn()}
        onDiscard={vi.fn()}
        onSealAndSend={vi.fn()}
      />
    );

    const input = screen.getByPlaceholderText(/Draft hint:/i);
    fireEvent.change(input, { target: { value: "Make it firmer on borders" } });

    const rewriteBtn = screen.getByRole("button", { name: /Rewrite/i });
    fireEvent.click(rewriteBtn);

    expect(handleRewrite).toHaveBeenCalledWith("Make it firmer on borders");
  });

  it("handles direct quill editing and discard", () => {
    const handleUpdateBody = vi.fn();
    const handleDiscard = vi.fn();

    render(
      <LetterDraftingStage
        pkg={DEFAULT_LETTER_SCENARIO}
        activeDraft={DEFAULT_LETTER_SCENARIO.initialDraft}
        mode="direct_quill"
        canUndo={false}
        canRedo={false}
        isSealing={false}
        onRewrite={vi.fn()}
        onUpdateBody={handleUpdateBody}
        onUndo={vi.fn()}
        onRedo={vi.fn()}
        onDiscard={handleDiscard}
        onSealAndSend={vi.fn()}
      />
    );

    const textarea = screen.getByRole("textbox", { name: /Direct quill editing/i });
    fireEvent.change(textarea, { target: { value: "Revised text by ruler." } });
    expect(handleUpdateBody).toHaveBeenCalledWith("Revised text by ruler.");

    const discardBtn = screen.getByRole("button", { name: /Discard/i });
    fireEvent.click(discardBtn);
    expect(handleDiscard).toHaveBeenCalled();
  });

  it("triggers undo and redo callbacks", () => {
    const handleUndo = vi.fn();
    const handleRedo = vi.fn();

    render(
      <LetterDraftingStage
        pkg={DEFAULT_LETTER_SCENARIO}
        activeDraft={DEFAULT_LETTER_SCENARIO.initialDraft}
        mode="scribe"
        canUndo={true}
        canRedo={true}
        isSealing={false}
        onRewrite={vi.fn()}
        onUpdateBody={vi.fn()}
        onUndo={handleUndo}
        onRedo={handleRedo}
        onDiscard={vi.fn()}
        onSealAndSend={vi.fn()}
      />
    );

    const undoBtn = screen.getByRole("button", { name: /Undo draft change/i });
    fireEvent.click(undoBtn);
    expect(handleUndo).toHaveBeenCalled();

    const redoBtn = screen.getByRole("button", { name: /Redo draft change/i });
    fireEvent.click(redoBtn);
    expect(handleRedo).toHaveBeenCalled();
  });
});

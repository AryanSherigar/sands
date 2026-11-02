import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { LetterPouchStage } from "../LetterPouchStage";
import { DEFAULT_LETTER_SCENARIO } from "../../fixtures/defaultLetterScenario";

describe("LetterPouchStage", () => {
  it("renders Queen Mira's provenance, letter manuscript, and reply dockets", () => {
    const onSelectDocket = vi.fn();
    render(
      <LetterPouchStage
        pkg={DEFAULT_LETTER_SCENARIO}
        onSelectDocket={onSelectDocket}
      />
    );

    expect(screen.getByText("Queen Mira")).toBeInTheDocument();
    expect(screen.getByText(/Send two grain barges downriver/i)).toBeInTheDocument();
    expect(screen.getByText("Broken wax seal")).toBeInTheDocument();

    const writeBtn = screen.getByRole("button", { name: /Write it myself/i });
    fireEvent.click(writeBtn);
    expect(onSelectDocket).toHaveBeenCalledWith("write");

    const scribeBtn = screen.getByRole("button", { name: /Ask my scribe/i });
    fireEvent.click(scribeBtn);
    expect(onSelectDocket).toHaveBeenCalledWith("scribe");

    const asideBtn = screen.getByRole("button", { name: /Set it aside/i });
    fireEvent.click(asideBtn);
    expect(onSelectDocket).toHaveBeenCalledWith("aside");
  });

  it("offers to decline the letter and reports the choice", () => {
    const onSelect = vi.fn();
    render(<LetterPouchStage pkg={DEFAULT_LETTER_SCENARIO} onSelectDocket={onSelect} />);

    fireEvent.click(screen.getByRole("button", { name: /Decline to answer/i }));

    expect(onSelect).toHaveBeenCalledWith("decline");
  });

  it("hides the decline option when the letter cannot be declined", () => {
    const pkg = { ...DEFAULT_LETTER_SCENARIO, isDeclinable: false };
    render(<LetterPouchStage pkg={pkg} onSelectDocket={vi.fn()} />);

    expect(screen.queryByRole("button", { name: /Decline to answer/i })).toBeNull();
  });
});

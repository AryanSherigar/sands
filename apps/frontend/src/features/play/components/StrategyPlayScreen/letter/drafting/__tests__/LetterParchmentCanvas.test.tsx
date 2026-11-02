import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { DraftRevision } from "../../../../../types/letterScene.types";
import { LetterParchmentCanvas } from "../LetterParchmentCanvas";

const draft = (paragraphs: string[]): DraftRevision => ({
  revisionIndex: 1,
  instruction: "",
  salutation: "",
  paragraphs,
  signoffText: "",
  authorTitle: "",
});

describe("LetterParchmentCanvas", () => {
  it("shows every paragraph of a long scribe draft", () => {
    const paragraphs = ["One.", "Two.", "Three.", "Four.", "Five."];
    render(
      <LetterParchmentCanvas
        draft={draft(paragraphs)}
        isDirectQuill={false}
        onUpdateBody={vi.fn()}
      />,
    );

    for (const text of paragraphs) {
      expect(screen.getByText(text)).toBeInTheDocument();
    }
  });

  it("splits a body with blank lines into paragraphs when reading", () => {
    render(
      <LetterParchmentCanvas
        draft={draft(["Alpha.\n\nBeta."])}
        isDirectQuill={false}
        onUpdateBody={vi.fn()}
      />,
    );

    expect(screen.getByText("Alpha.")).toBeInTheDocument();
    expect(screen.getByText("Beta.")).toBeInTheDocument();
  });

  it("offers one editable body holding the whole text in direct quill mode", () => {
    const onUpdateBody = vi.fn();
    render(
      <LetterParchmentCanvas
        draft={draft(["One.", "Two."])}
        isDirectQuill
        onUpdateBody={onUpdateBody}
      />,
    );

    const quill = screen.getByRole("textbox", { name: /Direct quill editing/i });
    expect(quill).toHaveValue("One.\n\nTwo.");
    fireEvent.change(quill, { target: { value: "One.\n\nTwo.\n\nThree." } });
    expect(onUpdateBody).toHaveBeenCalledWith("One.\n\nTwo.\n\nThree.");
  });

  it("gives an empty draft an empty editable body so the ruler can start writing", () => {
    render(
      <LetterParchmentCanvas draft={draft([""])} isDirectQuill onUpdateBody={vi.fn()} />,
    );

    expect(screen.getByRole("textbox", { name: /Direct quill editing/i })).toHaveValue("");
  });

  it("invites the ruler to ask the scribe when an empty draft is only being read", () => {
    render(
      <LetterParchmentCanvas
        draft={draft([""])}
        isDirectQuill={false}
        onUpdateBody={vi.fn()}
      />,
    );

    expect(screen.getByText(/ask your scribe/i)).toBeInTheDocument();
  });

  it("carries no fixture text", () => {
    render(
      <LetterParchmentCanvas
        draft={draft(["Words."])}
        isDirectQuill={false}
        onUpdateBody={vi.fn()}
      />,
    );

    expect(document.body.textContent).not.toMatch(/Aldric|Marches Council|Line 8/);
  });
});

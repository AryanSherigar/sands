import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { usePlayStore } from "../../../../stores/play.store";
import { HighlightedParagraph } from "../HighlightedParagraph";

const LONG_PARAGRAPH = Array.from({ length: 600 }, (_, i) => `corridor${i}`).join(
  " ",
);

const distortion = {
  playthroughId: "pt-1",
  turnNumber: 2,
  paragraphIndex: 0,
  isComplete: true,
};

const baseProps = {
  paragraph: LONG_PARAGRAPH,
  isFirst: false,
  fontClass: "font-narration-inter",
};

describe("HighlightedParagraph distortion", () => {
  beforeEach(() => {
    usePlayStore.setState({ reader_font_size: "medium" });
  });

  it("renders plain text with no eerie words when no distortion is given", () => {
    const { container } = render(<HighlightedParagraph {...baseProps} />);

    expect(container.querySelectorAll(".font-eerie")).toHaveLength(0);
    expect(container.textContent).toBe(LONG_PARAGRAPH);
  });

  it("wraps about 5% of the words and keeps every character", () => {
    const { container } = render(
      <HighlightedParagraph {...baseProps} distortion={distortion} />,
    );

    const eerie = container.querySelectorAll(".font-eerie").length;
    expect(eerie).toBeGreaterThan(15);
    expect(eerie).toBeLessThan(45);
    expect(container.textContent).toBe(LONG_PARAGRAPH);
  });

  it("renders the same words eerie on every render", () => {
    const first = render(
      <HighlightedParagraph {...baseProps} distortion={distortion} />,
    );
    const firstHtml = first.container.innerHTML;
    first.unmount();

    const second = render(
      <HighlightedParagraph {...baseProps} distortion={distortion} />,
    );

    expect(second.container.innerHTML).toBe(firstHtml);
  });

  it("appends trailing content after the text", () => {
    render(
      <HighlightedParagraph
        {...baseProps}
        paragraph="short text"
        trailing={<span data-testid="cursor" />}
      />,
    );

    expect(screen.getByTestId("cursor")).toBeInTheDocument();
  });
});

describe("HighlightedParagraph drop cap", () => {
  beforeEach(() => {
    usePlayStore.setState({ reader_font_size: "medium" });
  });

  it("skips the drop cap when the first word is one letter", () => {
    const { container } = render(
      <HighlightedParagraph paragraph="A single lamp is on." isFirst fontClass="f" />,
    );
    expect(container.querySelector("p")?.className).not.toContain(
      "first-letter:float-left",
    );
    expect(container.textContent).toBe("A single lamp is on.");
  });

  it("keeps the drop cap for a longer first word", () => {
    const { container } = render(
      <HighlightedParagraph paragraph="The lamp is on." isFirst fontClass="f" />,
    );
    expect(container.querySelector("p")?.className).toContain(
      "first-letter:float-left",
    );
  });
});

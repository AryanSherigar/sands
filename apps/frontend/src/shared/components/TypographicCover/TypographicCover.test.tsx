import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { TypographicCover } from "./TypographicCover";

describe("TypographicCover", () => {
  it("sets the title on the primary genre accent", () => {
    render(<TypographicCover title="The Lighthouse" primaryGenre="Horror" />);

    const cover = screen.getByRole("img", { name: "The Lighthouse" });
    expect(cover.className).toContain("[--accent:208_119_124]");
    expect(screen.getByText("The Lighthouse")).toBeInTheDocument();
  });

  it("stays neutral when the story has no genre", () => {
    render(<TypographicCover title="Untitled" primaryGenre={null} />);

    const cover = screen.getByRole("img", { name: "Untitled" });
    expect(cover.className).not.toContain("[--accent:208_119_124]");
    expect(cover.className).toContain("bg-surface-raised");
  });

  it("wraps a very long title to three lines then truncates", () => {
    const longTitle = "A ".repeat(120).trim();
    render(<TypographicCover title={longTitle} primaryGenre="Mystery" />);

    const title = screen.getByText(longTitle);
    expect(title.className).toContain("line-clamp-3");
    expect(title.className).toContain("break-words");
  });

  it("falls back to a quiet placeholder when the title is empty", () => {
    render(<TypographicCover title="   " primaryGenre="Mystery" />);

    expect(screen.getByRole("img", { name: "Untitled story" })).toBeInTheDocument();
  });
});

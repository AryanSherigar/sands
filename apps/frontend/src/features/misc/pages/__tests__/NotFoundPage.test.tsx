import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { NotFoundPage } from "../NotFoundPage";

describe("NotFoundPage", () => {
  const renderNotFound = () =>
    render(
      <MemoryRouter>
        <NotFoundPage />
      </MemoryRouter>,
    );

  it("renders 404 text, description, and return home link", () => {
    renderNotFound();

    expect(screen.getByText("404")).toBeInTheDocument();
    expect(screen.getByText("This path leads nowhere")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Back to sands" })).toHaveAttribute(
      "href",
      "/",
    );
  });

  it("renders the arcane rune glyph button", () => {
    renderNotFound();

    const runeButton = screen.getByRole("button", {
      name: /commune with the arcane rune/i,
    });
    expect(runeButton).toBeInTheDocument();
  });

  it("toggles the mystic terminal when clicking the rune", () => {
    renderNotFound();

    expect(
      screen.queryByText(/sands void terminal/i),
    ).not.toBeInTheDocument();

    const runeButton = screen.getByRole("button", {
      name: /commune with the arcane rune/i,
    });
    fireEvent.click(runeButton);

    expect(screen.getByText(/sands void terminal/i)).toBeInTheDocument();

    fireEvent.click(runeButton);
    expect(
      screen.queryByText(/sands void terminal/i),
    ).not.toBeInTheDocument();
  });

  it("toggles the terminal via tilde shortcut", () => {
    renderNotFound();

    fireEvent.keyDown(window, { key: "~" });
    expect(screen.getByText(/sands void terminal/i)).toBeInTheDocument();

    fireEvent.keyDown(window, { key: "Escape" });
    expect(
      screen.queryByText(/sands void terminal/i),
    ).not.toBeInTheDocument();
  });
});

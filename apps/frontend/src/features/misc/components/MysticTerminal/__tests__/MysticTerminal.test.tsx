import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { MysticTerminal } from "../MysticTerminal";

describe("MysticTerminal", () => {
  const defaultProps = {
    is_open: true,
    onClose: vi.fn(),
  };

  const renderTerminal = (props = defaultProps) =>
    render(
      <MemoryRouter>
        <MysticTerminal {...props} />
      </MemoryRouter>,
    );

  it("renders terminal header and welcome lines when open", () => {
    renderTerminal();

    expect(screen.getByText(/sands void terminal/i)).toBeInTheDocument();
    expect(screen.getByText(/attuned to the resonance/i)).toBeInTheDocument();
  });

  it("does not render when is_open is false", () => {
    renderTerminal({ ...defaultProps, is_open: false });

    expect(
      screen.queryByText(/sands void terminal/i),
    ).not.toBeInTheDocument();
  });

  it("executes command when clicking quick action chips", () => {
    renderTerminal();

    const animeChip = screen.getByRole("button", { name: "anime" });
    fireEvent.click(animeChip);

    const animeMatches = [
      ...screen.queryAllByText(/re:zero/i),
      ...screen.queryAllByText(/grimgar/i),
      ...screen.queryAllByText(/grieving souls/i),
    ];
    expect(animeMatches.length).toBeGreaterThan(0);
  });

  it("executes command entered into prompt input", () => {
    renderTerminal();

    const input = screen.getByLabelText(/terminal prompt/i);
    fireEvent.change(input, { target: { value: "song" } });
    fireEvent.keyDown(input, { key: "Enter" });

    const songMatches = [
      ...screen.queryAllByText(/i cannot say/i),
      ...screen.queryAllByText(/song of the ancients/i),
    ];
    expect(songMatches.length).toBeGreaterThan(0);
  });

  it("clears terminal output when clear command is executed", () => {
    renderTerminal();

    const clearChip = screen.getByRole("button", { name: "clear" });
    fireEvent.click(clearChip);

    expect(
      screen.queryByText(/attuned to the resonance/i),
    ).not.toBeInTheDocument();
  });

  it("displays help commands list", () => {
    renderTerminal();

    const helpChip = screen.getByRole("button", { name: "help" });
    fireEvent.click(helpChip);

    expect(screen.getByText(/Available commands:/i)).toBeInTheDocument();
  });
});

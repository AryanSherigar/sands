import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { StudioShowcaseBand } from "../StudioShowcaseBand";

vi.mock("@/shared/hooks/useIsAlphaMode", () => ({
  useIsAlphaMode: () => false,
}));

describe("StudioShowcaseBand", () => {
  it("renders the authentic authoring architecture showcase", () => {
    render(
      <MemoryRouter>
        <StudioShowcaseBand />
      </MemoryRouter>,
    );

    expect(screen.getByText("Authoring Architecture")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Two ways to build worlds" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Simple Mode")).toBeInTheDocument();
    expect(screen.getByText("Advanced Mode")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /Open Studio/i }),
    ).toHaveAttribute("href", "/studio");

    // Real architecture status
    expect(screen.getByText("SCHEMA VALID")).toBeInTheDocument();
    expect(
      screen.getByText(/Deterministic engine idle/),
    ).toBeInTheDocument();
    expect(screen.getByText("latency: 42ms")).toBeInTheDocument();
  });

  it("toggles between Advanced and Simple mode YAML previews", async () => {
    render(
      <MemoryRouter>
        <StudioShowcaseBand />
      </MemoryRouter>,
    );
    const user = userEvent.setup();

    // Default is advanced
    expect(
      screen.getByText("· archivist_core.rules.yaml"),
    ).toBeInTheDocument();
    expect(screen.getByText("invariant_rules:")).toBeInTheDocument();

    // Click Simple tab
    await user.click(screen.getByRole("button", { name: "Simple" }));
    expect(screen.getByText("· hollow_cairn.yaml")).toBeInTheDocument();
    expect(screen.getByText("narrator_mandate:")).toBeInTheDocument();

    // Click Advanced tab
    await user.click(screen.getByRole("button", { name: "Advanced" }));
    expect(
      screen.getByText("· archivist_core.rules.yaml"),
    ).toBeInTheDocument();
  });
});

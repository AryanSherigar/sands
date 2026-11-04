import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { TopCanopyControls } from "../TopCanopyControls";

describe("TopCanopyControls Proclamation", () => {
  it("renders the Issue Proclamation button with 2 mandates indicator", () => {
    render(<TopCanopyControls mandatesRemaining={3} onIssueProclamation={vi.fn()} />);
    expect(screen.getByRole("button", { name: /issue proclamation/i })).toBeInTheDocument();
  });

  it("disables the button when mandates are under 2", () => {
    render(<TopCanopyControls mandatesRemaining={1} onIssueProclamation={vi.fn()} />);
    expect(screen.getByRole("button", { name: /issue proclamation/i })).toBeDisabled();
  });

  it("renders the active edict pill when an edict is in force", () => {
    render(
      <TopCanopyControls
        mandatesRemaining={3}
        activeEdict={{ title: "War Silver Levy", remainingTurns: 3 }}
        onIssueProclamation={vi.fn()}
      />
    );
    expect(screen.getByText(/Edict: War Silver Levy/i)).toBeInTheDocument();
  });

  it("lists the edict's ongoing effects in the pill's tooltip", () => {
    render(
      <TopCanopyControls
        mandatesRemaining={3}
        activeEdict={{ title: "War Silver Levy", remainingTurns: 3, effects: ["+15 points of tax", "-10% trade income"] }}
        onIssueProclamation={vi.fn()}
      />
    );
    const pill = screen.getByText(/Edict: War Silver Levy/i).closest("div");
    expect(pill).toHaveAttribute("title", expect.stringContaining("+15 points of tax"));
    expect(pill).toHaveAttribute("title", expect.stringContaining("-10% trade income"));
  });
});

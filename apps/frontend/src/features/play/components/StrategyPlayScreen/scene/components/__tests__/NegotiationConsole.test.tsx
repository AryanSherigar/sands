import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { NegotiationConsole } from "../NegotiationConsole";

describe("NegotiationConsole", () => {
  it("submits speech on enter and clicking Speak", () => {
    const handleSend = vi.fn();
    render(<NegotiationConsole onSend={handleSend} onToggleDrawer={vi.fn()} onBreakTalks={vi.fn()} />);

    const input = screen.getByPlaceholderText(/speak to/i);
    fireEvent.change(input, { target: { value: "We seek peace." } });

    const speakBtn = screen.getByRole("button", { name: /speak/i });
    fireEvent.click(speakBtn);

    expect(handleSend).toHaveBeenCalledWith("We seek peace.");
  });

  it("handles Offer drawer toggle and Break Talks confirmation", () => {
    const handleToggleDrawer = vi.fn();
    const handleBreakTalks = vi.fn();

    render(
      <NegotiationConsole
        onSend={vi.fn()}
        onToggleDrawer={handleToggleDrawer}
        onBreakTalks={handleBreakTalks}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: /^offer$/i }));
    expect(handleToggleDrawer).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByRole("button", { name: /break talks/i }));
    expect(screen.getByText(/Are you sure you want to walk away/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /confirm break talks/i }));
    expect(handleBreakTalks).toHaveBeenCalledTimes(1);
  });
});

describe("NegotiationConsole clause builder", () => {
  it("fills the speech box with a drafted sentence instead of sending it", () => {
    const onSend = vi.fn();
    render(<NegotiationConsole onSend={onSend} onToggleDrawer={vi.fn()} onBreakTalks={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: "Draft a clause" }));
    fireEvent.change(screen.getByLabelText("When it applies"), { target: { value: "trigger" } });
    fireEvent.click(screen.getByRole("button", { name: "Use this sentence" }));

    expect(onSend).not.toHaveBeenCalled();
    expect(screen.getByRole("textbox")).toHaveValue(
      "Once my treasury is below 100 gold, I will pay you 50 gold. Let this agreement lapse after 10 turns.",
    );
  });

  it("limits gates to clauses that continue", () => {
    render(<NegotiationConsole onSend={vi.fn()} onToggleDrawer={vi.fn()} onBreakTalks={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: "Draft a clause" }));
    fireEvent.change(screen.getByLabelText("When it applies"), { target: { value: "gate" } });

    expect(screen.queryByRole("option", { name: "A payment of gold" })).toBeNull();
    expect(screen.getByRole("option", { name: "A trade deal" })).toBeInTheDocument();
  });

  it("builds a plain clause with no condition by default", () => {
    render(<NegotiationConsole onSend={vi.fn()} onToggleDrawer={vi.fn()} onBreakTalks={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: "Draft a clause" }));
    fireEvent.click(screen.getByRole("button", { name: "Use this sentence" }));

    expect(screen.getByRole("textbox")).toHaveValue("I will pay you 50 gold.");
  });

  it("joins several clauses into one proposal", () => {
    render(<NegotiationConsole onSend={vi.fn()} onToggleDrawer={vi.fn()} onBreakTalks={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: "Draft a clause" }));
    fireEvent.click(screen.getByRole("button", { name: "Add another clause" }));
    const clauseSelects = screen.getAllByLabelText("The clause");
    fireEvent.change(clauseSelects[1], { target: { value: "trade_deal" } });
    fireEvent.click(screen.getByRole("button", { name: "Use this sentence" }));

    expect(screen.getByRole("textbox")).toHaveValue("I will pay you 50 gold. We will keep a trade deal.");
  });

  it("offers region clauses only when the scene lists regions, and needs one chosen", () => {
    const regions = [{ id: "dunmere", name: "Dunmere" }];
    render(
      <NegotiationConsole regions={regions} onSend={vi.fn()} onToggleDrawer={vi.fn()} onBreakTalks={vi.fn()} />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Draft a clause" }));
    fireEvent.change(screen.getByLabelText("The clause"), { target: { value: "region_promise" } });
    expect(screen.getByRole("button", { name: "Use this sentence" })).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Region"), { target: { value: "dunmere" } });
    fireEvent.click(screen.getByRole("button", { name: "Use this sentence" }));

    expect(screen.getByRole("textbox")).toHaveValue("I swear never to occupy Dunmere.");
  });

  it("hides region clauses when the scene lists none", () => {
    render(<NegotiationConsole onSend={vi.fn()} onToggleDrawer={vi.fn()} onBreakTalks={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: "Draft a clause" }));

    expect(screen.queryByRole("option", { name: "Handing over a region" })).toBeNull();
  });
});

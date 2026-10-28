import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { StrategyOrdersTray } from "../StrategyOrdersTray";
import { StrategyEndTurnModule } from "../StrategyEndTurnModule";
import type { QueuedOrderView } from "../../../../types/simulation.types";

const mockOrders: QueuedOrderView[] = [
  {
    id: "cmd-1",
    order: {
      kind: "raise_army",
      faction_id: "f1",
      region_id: "reg-dunmere",
      troops: { infantry: 350 },
    },
    cost: 1,
    queued_turn: 1,
    is_cancellable: true,
  },
];

describe("StrategyOrdersTray", () => {
  it("renders queued order and cancel trigger", () => {
    const onCancel = vi.fn();
    render(<StrategyOrdersTray orders={mockOrders} onCancelOrder={onCancel} />);
    expect(screen.getByText("Levy troops in Reg-dunmere")).toBeInTheDocument();
    fireEvent.click(screen.getByTitle("Cancel order"));
    expect(onCancel).toHaveBeenCalledWith("cmd-1");
  });

  it("shows region names when a lookup is provided", () => {
    render(
      <StrategyOrdersTray
        orders={mockOrders}
        regionNames={{ "reg-dunmere": "Dunmere Vale" }}
        onCancelOrder={vi.fn()}
      />,
    );
    expect(screen.getByText("Levy troops in Dunmere Vale")).toBeInTheDocument();
  });

  it("renders open mandates when remaining orders exist", () => {
    render(
      <StrategyOrdersTray
        orders={mockOrders}
        ordersRemaining={3}
        onCancelOrder={vi.fn()}
      />,
    );
    expect(screen.getByText("3 / 3 Mandates Open")).toBeInTheDocument();
  });

  it("does not render cancel button when order is not cancellable", () => {
    const nonCancellableOrder = [
      {
        ...mockOrders[0],
        is_cancellable: false,
      },
    ];
    render(
      <StrategyOrdersTray
        orders={nonCancellableOrder}
        onCancelOrder={vi.fn()}
      />,
    );
    expect(screen.queryByTitle("Cancel order")).not.toBeInTheDocument();
  });
});

describe("StrategyEndTurnModule", () => {
  it("ends the turn immediately when no mandates are unspent", () => {
    const onEndTurn = vi.fn();
    render(
      <StrategyEndTurnModule ordersRemaining={0} onEndTurn={onEndTurn} />,
    );
    fireEvent.click(screen.getByRole("button", { name: /end turn/i }));
    expect(onEndTurn).toHaveBeenCalledTimes(1);
  });

  it("asks for confirmation before ending with unspent mandates", () => {
    const onEndTurn = vi.fn();
    render(
      <StrategyEndTurnModule ordersRemaining={3} onEndTurn={onEndTurn} />,
    );
    fireEvent.click(screen.getByRole("button", { name: /end turn/i }));
    expect(onEndTurn).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "End turn" }));
    expect(onEndTurn).toHaveBeenCalledTimes(1);
  });

  it("keeps planning when the confirmation is declined", () => {
    const onEndTurn = vi.fn();
    render(
      <StrategyEndTurnModule ordersRemaining={3} onEndTurn={onEndTurn} />,
    );
    fireEvent.click(screen.getByRole("button", { name: /end turn/i }));
    fireEvent.click(screen.getByRole("button", { name: "Keep planning" }));
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
    expect(onEndTurn).not.toHaveBeenCalled();
  });

  it("disables button when loading", () => {
    const onEndTurn = vi.fn();
    render(
      <StrategyEndTurnModule
        ordersRemaining={3}
        isLoading={true}
        onEndTurn={onEndTurn}
      />,
    );
    const button = screen.getByRole("button", { name: /advancing/i });
    expect(button).toBeDisabled();
    fireEvent.click(button);
    expect(onEndTurn).not.toHaveBeenCalled();
  });

  it("displays next season in button sublabel", () => {
    render(
      <StrategyEndTurnModule
        ordersRemaining={3}
        nextSeason="Spring 1043"
        onEndTurn={vi.fn()}
      />,
    );
    expect(
      screen.getByText(/Advances 2 mos · Spring 1043/),
    ).toBeInTheDocument();
  });
});

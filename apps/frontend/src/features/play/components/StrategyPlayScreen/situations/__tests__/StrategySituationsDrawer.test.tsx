import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { StrategySituationsDrawer } from "../StrategySituationsDrawer";
import { makeSituation } from "../../../../test-utils/eventFixtures";
import type { ActiveSituation } from "../../../../types/situation.types";

function renderDrawer(situations: ActiveSituation[], overrides = {}) {
  const props = {
    isOpen: true,
    situations,
    ordersRemaining: 4,
    onClose: vi.fn(),
    onCenterMap: vi.fn(),
    onExecuteLever: vi.fn(),
    onCancelLever: vi.fn(),
    onReviewEvent: vi.fn(),
    ...overrides,
  };
  render(<StrategySituationsDrawer {...props} />);
  return props;
}

describe("StrategySituationsDrawer", () => {
  it("renders nothing when closed", () => {
    const { container } = render(
      <StrategySituationsDrawer
        isOpen={false}
        situations={[makeSituation()]}
        ordersRemaining={4}
        onClose={vi.fn()}
        onCenterMap={vi.fn()}
        onExecuteLever={vi.fn()}
        onCancelLever={vi.fn()}
        onReviewEvent={vi.fn()}
      />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("shows the real number of orders left and the crisis count", () => {
    renderDrawer([makeSituation(), makeSituation({ id: "situation-event_2", eventId: "event_2" })]);
    expect(screen.getByText("2 Active Crises")).toBeDefined();
    expect(screen.getByText("Orders left: 4. You cannot mend everything.")).toBeDefined();
  });

  it("closes on the close button and on Escape", () => {
    const props = renderDrawer([makeSituation()]);
    fireEvent.click(screen.getByRole("button", { name: /close/i }));
    fireEvent.keyDown(window, { key: "Escape" });
    expect(props.onClose).toHaveBeenCalledTimes(2);
  });

  it("shows an empty state when there is nothing to handle", () => {
    renderDrawer([]);
    expect(screen.getByText("No active crises")).toBeDefined();
  });

  it("draws the severity ladder from the template's own stages", () => {
    renderDrawer([makeSituation()]);
    expect(screen.getByText("1. Murmurs")).toBeDefined();
    expect(screen.getByText("2. Petition")).toBeDefined();
    expect(screen.getByText("3. Revolt looms")).toBeDefined();
    expect(screen.queryByText(/^4\. /)).toBeNull();
  });

  it("states the answer deadline rather than inventing a countdown", () => {
    renderDrawer([makeSituation()]);
    expect(screen.getByText("Answer this turn")).toBeDefined();
    expect(screen.queryByText(/Next stage in/i)).toBeNull();
    expect(screen.queryByText(/Resolution Progress/i)).toBeNull();
  });

  it("shows the real cause, intelligence and the neglect consequence", () => {
    renderDrawer([makeSituation()]);
    expect(
      screen.getByText(/Because unrest is 62 and the governor's opinion of you is −40\./),
    ).toBeDefined();
    expect(screen.getByText("Unrest is 62")).toBeDefined();
    expect(screen.getByText("If unanswered by the next turn: Unrest +10.")).toBeDefined();
  });

  it("lists each lever with its order cost and effects and orders it on click", () => {
    const props = renderDrawer([makeSituation()]);
    expect(screen.getByText("Lighten the levy in this region")).toBeDefined();
    expect(screen.getByText("1 Order")).toBeDefined();
    expect(screen.getByText("Unrest −10")).toBeDefined();
    fireEvent.click(screen.getByRole("button", { name: "Order this" }));
    expect(props.onExecuteLever).toHaveBeenCalledWith(
      expect.objectContaining({ eventId: "event_1", choiceId: "ease_taxes" }),
    );
  });

  it("disables a lever the player cannot afford", () => {
    const situation = makeSituation();
    situation.levers[0].isAffordable = false;
    const props = renderDrawer([situation]);
    const button = screen.getByRole("button", { name: "Can't afford" }) as HTMLButtonElement;
    expect(button.disabled).toBe(true);
    fireEvent.click(button);
    expect(props.onExecuteLever).not.toHaveBeenCalled();
  });

  it("offers cancelling a queued lever instead of ordering it again", () => {
    const situation = makeSituation();
    situation.levers[0].isQueued = true;
    situation.levers[0].queuedCommandId = "cmd-7";
    const props = renderDrawer([situation]);
    expect(screen.queryByRole("button", { name: "Order this" })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: /Queued — cancel/ }));
    expect(props.onCancelLever).toHaveBeenCalledWith("cmd-7");
  });

  it("opens the decision for a pending event", () => {
    const props = renderDrawer([makeSituation()]);
    fireEvent.click(screen.getByRole("button", { name: "Review decision" }));
    expect(props.onReviewEvent).toHaveBeenCalledWith("event_1");
  });

  it("shows an ongoing problem without levers or a review button", () => {
    renderDrawer([
      makeSituation({
        id: "situation-memory-tax_grievance-ashford",
        eventId: null,
        isActionable: false,
        deadlineTurn: null,
        levers: [],
        ifIgnoredWarning: null,
      }),
    ]);
    expect(screen.getByText("Ongoing")).toBeDefined();
    expect(screen.queryByRole("button", { name: "Review decision" })).toBeNull();
    expect(screen.queryByText("Intervention Levers")).toBeNull();
    expect(screen.getByText("No decision is waiting on this right now.")).toBeDefined();
  });

  it("centers the map on the situation's region", () => {
    const props = renderDrawer([makeSituation()]);
    fireEvent.click(screen.getByRole("button", { name: /Center map on Ashford Vale/ }));
    expect(props.onCenterMap).toHaveBeenCalledWith("ashford");
  });

  it("omits the map button for a situation with no region", () => {
    renderDrawer([makeSituation({ regionId: null, regionName: "House Carrow" })]);
    expect(screen.queryByRole("button", { name: /Center map/ })).toBeNull();
  });

  it("highlights the active situation", () => {
    renderDrawer([makeSituation()], { activeSituationId: "situation-event_1" });
    expect(screen.getByTestId("situation-card-situation-event_1").className).toContain(
      "border-tertiary",
    );
  });
});

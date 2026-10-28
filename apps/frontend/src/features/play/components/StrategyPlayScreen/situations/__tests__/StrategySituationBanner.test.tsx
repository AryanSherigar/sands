import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { StrategySituationBanner } from "../StrategySituationBanner";
import { makeSituation } from "../../../../test-utils/eventFixtures";

function renderBanner(situation = makeSituation()) {
  const props = { onCenterMap: vi.fn(), onReviewEvent: vi.fn(), onDismiss: vi.fn() };
  render(<StrategySituationBanner situation={situation} {...props} />);
  return props;
}

describe("StrategySituationBanner", () => {
  it("announces the event with its real cause and stage", () => {
    renderBanner();
    expect(screen.getByText("Grievance in Ashford Vale")).toBeDefined();
    expect(
      screen.getByText("Because unrest is 62 and the governor's opinion of you is −40."),
    ).toBeDefined();
    expect(screen.getByText("Stage 2: Petition")).toBeDefined();
  });

  it("centers the map, opens the decision and dismisses", () => {
    const props = renderBanner();
    fireEvent.click(screen.getByRole("button", { name: /Center map on Ashford Vale/i }));
    fireEvent.click(screen.getByRole("button", { name: "Review decision" }));
    fireEvent.click(screen.getByRole("button", { name: /Dismiss banner/i }));
    expect(props.onCenterMap).toHaveBeenCalledWith("ashford");
    expect(props.onReviewEvent).toHaveBeenCalledWith("event_1");
    expect(props.onDismiss).toHaveBeenCalledTimes(1);
  });

  it("omits the map button when the event has no region", () => {
    renderBanner(makeSituation({ regionId: null }));
    expect(screen.queryByRole("button", { name: /Center map/i })).toBeNull();
  });

  it("omits the review button for an ongoing problem", () => {
    renderBanner(makeSituation({ eventId: null }));
    expect(screen.queryByRole("button", { name: "Review decision" })).toBeNull();
  });
});

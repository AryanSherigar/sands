import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { StrategySituationPins } from "../StrategySituationPins";
import { makeSituation } from "../../../../test-utils/eventFixtures";

const centroids = {
  ashford: { x: 200, y: 300 },
  oakhaven: { x: 400, y: 500 },
};

function renderPins(situations = [makeSituation()], onSelect = vi.fn()) {
  render(
    <svg>
      <StrategySituationPins
        situations={situations}
        centroids={centroids}
        onSelectSituation={onSelect}
      />
    </svg>,
  );
  return onSelect;
}

describe("StrategySituationPins", () => {
  it("pins a situation at its region and reports clicks", () => {
    const onSelect = renderPins();
    const pin = screen.getByTestId("situation-pin-ashford");
    expect(pin.getAttribute("transform")).toBe("translate(200, 300)");
    fireEvent.click(pin);
    expect(onSelect).toHaveBeenCalledWith("situation-event_1", "ashford");
  });

  it("skips a situation with no region and one with no known position", () => {
    renderPins([
      makeSituation({ id: "a", regionId: null }),
      makeSituation({ id: "b", regionId: "unmapped" }),
    ]);
    expect(screen.queryByTestId(/situation-pin-/)).toBeNull();
  });

  it("pulses only escalated situations", () => {
    renderPins([
      makeSituation({ id: "mild", regionId: "oakhaven", severityStage: 1 }),
      makeSituation({ id: "severe", severityStage: 3 }),
    ]);
    const mild = screen.getByTestId("situation-pin-oakhaven");
    const severe = screen.getByTestId("situation-pin-ashford");
    expect(mild.querySelector(".animate-ping")).toBeNull();
    expect(severe.querySelector(".animate-ping")).not.toBeNull();
  });
});

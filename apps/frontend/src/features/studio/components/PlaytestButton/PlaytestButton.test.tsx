import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { PlaytestButton } from "./PlaytestButton";

const SCENARIO_ID = "scenario-1";

const SetupRouteProbe = () => {
  const location = useLocation();
  return (
    <div data-testid="setup-route">{location.pathname + location.search}</div>
  );
};

describe("PlaytestButton", () => {
  it("opens the setup screen in playtest mode so required fields can be filled", async () => {
    render(
      <MemoryRouter initialEntries={[`/studio/${SCENARIO_ID}/edit`]}>
        <Routes>
          <Route
            path="/studio/:id/edit"
            element={<PlaytestButton scenarioId={SCENARIO_ID} />}
          />
          <Route path="/setup/:id" element={<SetupRouteProbe />} />
        </Routes>
      </MemoryRouter>,
    );

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /playtest/i }));

    expect(screen.getByTestId("setup-route")).toHaveTextContent(
      `/setup/${SCENARIO_ID}?playtest=1`,
    );
  });
});

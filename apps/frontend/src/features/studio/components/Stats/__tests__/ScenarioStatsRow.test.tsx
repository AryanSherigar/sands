import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { buildOverview } from "../../../test/statsFixtures";
import { ScenarioStatsRow } from "../ScenarioStatsRow";

describe("ScenarioStatsRow", () => {
  it("lets the title link navigate without also firing the row click", async () => {
    const handleSelect = vi.fn();
    const [row] = buildOverview().scenarios;
    if (!row) throw new Error("fixture has no rows");
    render(
      <MemoryRouter>
        <table>
          <tbody>
            <ScenarioStatsRow row={row} range="30d" onSelect={handleSelect} />
          </tbody>
        </table>
      </MemoryRouter>,
    );

    await userEvent.click(screen.getByRole("link", { name: "The Hollow Cairn" }));

    expect(handleSelect).not.toHaveBeenCalled();
  });
});

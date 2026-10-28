import { fireEvent, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";
import { useStudioTabsStore } from "../../stores/studioTabs.store";
import { buildEntityFixture } from "../../test/cardApiMock";
import { renderStudio } from "../../test/renderStudio";
import {
  STUDIO_TEST_SCENARIO_ID,
  buildScenarioFixture,
  installStudioApi,
} from "../../test/studioApiMock";

const EDIT_PATH = `/studio/${STUDIO_TEST_SCENARIO_ID}/edit`;
const mara = buildEntityFixture({ entity_id: "mara", canonical_name: "Mara" });
const tomas = buildEntityFixture({ entity_id: "tomas", canonical_name: "Tomas" });

describe("tab right-click menu", () => {
  beforeEach(() => {
    localStorage.clear();
    useStudioTabsStore.getState().resetTabs();
    // @ts-expect-error jsdom has no matchMedia unless a test installs one
    delete window.matchMedia;
  });

  it("offers Split right, Close and Close others on right-click", async () => {
    installStudioApi({ scenario: buildScenarioFixture(), entities: [mara, tomas] });
    renderStudio({ path: EDIT_PATH });
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Mara" }));
    await user.click(screen.getByRole("button", { name: "Tomas" }));

    fireEvent.contextMenu(screen.getByRole("tab", { name: "Mara" }));
    const menu = await screen.findByRole("menu");
    expect(within(menu).getAllByRole("menuitem").map((item) => item.textContent)).toEqual([
      "Split right",
      "Close",
      "Close others",
    ]);

    await user.click(within(menu).getByRole("menuitem", { name: "Split right" }));
    expect(await screen.findByRole("region", { name: "Split tab" })).toBeInTheDocument();
  });

  it("closes the other tabs from the right-click menu", async () => {
    installStudioApi({ scenario: buildScenarioFixture(), entities: [mara, tomas] });
    renderStudio({ path: EDIT_PATH });
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Mara" }));
    await user.click(screen.getByRole("button", { name: "Tomas" }));

    fireEvent.contextMenu(screen.getByRole("tab", { name: "Tomas" }));
    await user.click(await screen.findByRole("menuitem", { name: "Close others" }));

    expect(screen.getAllByRole("tab").map((tab) => tab.textContent)).toEqual(["Tomas"]);
  });

  it("closes a tab from the right-click menu", async () => {
    installStudioApi({ scenario: buildScenarioFixture(), entities: [mara] });
    renderStudio({ path: EDIT_PATH });
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Mara" }));

    fireEvent.contextMenu(screen.getByRole("tab", { name: "Mara" }));
    await user.click(await screen.findByRole("menuitem", { name: "Close" }));

    expect(screen.queryByRole("tab", { name: "Mara" })).toBeNull();
  });
});

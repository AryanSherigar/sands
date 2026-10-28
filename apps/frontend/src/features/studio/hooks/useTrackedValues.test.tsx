import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { useStudioStore } from "../stores/studio.store";
import { useStudioTabsStore } from "../stores/studioTabs.store";
import { createGuideWrapper } from "../test/guideHookWrapper";
import { buildScenarioFixture, installStudioApi } from "../test/studioApiMock";
import { useGuide } from "./useGuide";
import { useTrackedValues } from "./useTrackedValues";

const HUD_METER = { kind: "meter", label: "Health", clamp_min: 0, clamp_max: 10 };

const renderTrackedValues = async (init: Parameters<typeof installStudioApi>[0]) => {
  const api = installStudioApi(init);
  const { Wrapper } = createGuideWrapper();
  const view = renderHook(() => useTrackedValues(), { wrapper: Wrapper });
  await waitFor(() => expect(view.result.current).toBeDefined());
  return { api, ...view };
};

describe("useTrackedValues", () => {
  beforeEach(() => {
    localStorage.clear();
    useStudioTabsStore.getState().resetTabs();
  });

  it("lists the tracked values of the story", async () => {
    const { result } = await renderTrackedValues({
      scenario: buildScenarioFixture({
        mode: "master",
        state_schema: { oil: { type: "number", label: "Lantern oil" }, note: { type: "string" } },
      }),
    });

    await waitFor(() => expect(result.current.values.map((value) => value.path)).toEqual(["oil"]));
  });

  it("saves a new value to the state schema and hands back the option", async () => {
    const { api, result } = await renderTrackedValues({ scenario: buildScenarioFixture({ mode: "master" }) });

    let created = null as Awaited<ReturnType<typeof result.current.addValue>> | null;
    await act(async () => {
      created = await result.current.addValue({ name: "Lantern oil", kind: "number", min: 0, max: 10, initial: 10 });
    });

    expect(created).toMatchObject({ path: "lantern_oil", label: "Lantern oil", kind: "number", source: "tracked" });
    expect(api.scenarioUpdates.at(-1)).toMatchObject({
      state_schema: { lantern_oil: { type: "number", label: "Lantern oil", initial: 10, min: 0, max: 10 } },
    });
    expect(api.toolPuts).toEqual([["status_hud"]]);
  });

  it("turns the status display on for a plain Number without an explicit display", async () => {
    const { api, result } = await renderTrackedValues({ scenario: buildScenarioFixture({ mode: "master" }) });

    await act(async () => {
      await result.current.addValue({ name: "Trust", kind: "number" });
    });

    expect(api.toolPuts).toEqual([["status_hud"]]);
    expect(api.scenario?.enabled_tools).toEqual(["status_hud"]);
  });

  it("leaves the status display off for a yes/no value", async () => {
    const { api, result } = await renderTrackedValues({ scenario: buildScenarioFixture({ mode: "master" }) });

    await act(async () => {
      await result.current.addValue({ name: "Has key", kind: "boolean" });
    });

    expect(api.toolPuts).toEqual([]);
  });

  it("turns the status HUD on before the first save of a value shown on screen", async () => {
    const { api, result } = await renderTrackedValues({ scenario: buildScenarioFixture({ mode: "master" }) });

    await act(async () => {
      await result.current.addValue({ name: "Health", kind: "number", min: 0, max: 10, display: HUD_METER });
    });

    expect(api.toolPuts).toEqual([["status_hud"]]);
    expect(api.writeLog).toEqual(["tools", "scenario:state_schema"]);
  });

  it("saves the value right after a tool switch without an edit conflict", async () => {
    const { api, result } = await renderTrackedValues({ scenario: buildScenarioFixture({ mode: "master" }) });

    await act(async () => {
      await result.current.addValue({ name: "Health", kind: "number", min: 0, max: 10, display: HUD_METER });
    });

    expect(useStudioStore.getState().hasEditConflict).toBe(false);
    expect(Object.keys(api.scenario?.state_schema ?? {})).toEqual(["health"]);
    expect(api.scenario?.enabled_tools).toEqual(["status_hud"]);
  });

  it("keeps a state schema edit that is still waiting to be saved", async () => {
    const api = installStudioApi({ scenario: buildScenarioFixture({ mode: "master" }) });
    const { Wrapper } = createGuideWrapper();
    const view = renderHook(() => ({ values: useTrackedValues(), guide: useGuide() }), { wrapper: Wrapper });
    await waitFor(() => expect(view.result.current.guide.scenario).not.toBeNull());

    await act(async () => {
      view.result.current.guide.saveFields({ state_schema: { trust: { type: "number", label: "Trust" } } });
      await view.result.current.values.addValue({ name: "Has key", kind: "boolean" });
    });

    expect(Object.keys(api.scenario?.state_schema ?? {})).toEqual(["trust", "has_key"]);
  });

  it("keeps earlier values when adding a second one", async () => {
    const { api, result } = await renderTrackedValues({ scenario: buildScenarioFixture({ mode: "master" }) });

    await act(async () => {
      await result.current.addValue({ name: "Trust", kind: "number" });
      await result.current.addValue({ name: "Has key", kind: "boolean" });
    });

    const schema = api.scenario?.state_schema ?? {};
    expect(Object.keys(schema)).toEqual(["trust", "has_key"]);
  });
});

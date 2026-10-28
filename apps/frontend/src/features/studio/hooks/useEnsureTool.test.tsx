import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { ToolsRequireAdvancedModeError } from "../lib/ensureTool";
import { useStudioTabsStore } from "../stores/studioTabs.store";
import { createGuideWrapper } from "../test/guideHookWrapper";
import { buildScenarioFixture, installStudioApi } from "../test/studioApiMock";
import { useEnsureTool } from "./useEnsureTool";
import { useGuide } from "./useGuide";

const renderEnsureTool = async (init: Parameters<typeof installStudioApi>[0]) => {
  const api = installStudioApi(init);
  const { Wrapper, queryClient } = createGuideWrapper();
  const view = renderHook(() => ({ ...useEnsureTool(), guide: useGuide() }), { wrapper: Wrapper });
  await waitFor(() => expect(view.result.current.guide.scenario).not.toBeNull());
  return { api, queryClient, ...view };
};

describe("useEnsureTool", () => {
  beforeEach(() => {
    localStorage.clear();
    useStudioTabsStore.getState().resetTabs();
  });

  it("turns a missing tool on through the tools endpoint", async () => {
    const { api, result } = await renderEnsureTool({ scenario: buildScenarioFixture({ mode: "master" }) });

    await act(() => result.current.ensureTool("rule_checks"));

    expect(api.toolPuts).toEqual([["rule_checks"]]);
    await waitFor(() => expect(result.current.guide.scenario?.enabled_tools).toEqual(["rule_checks"]));
  });

  it("does nothing when the tool is already on", async () => {
    const { api, result } = await renderEnsureTool({
      scenario: buildScenarioFixture({ mode: "master" }),
      enabledTools: ["rule_sheet"],
    });

    await act(() => result.current.ensureTool("rule_sheet"));

    expect(api.toolPuts).toEqual([]);
  });

  it("brings the status HUD along with atmosphere", async () => {
    const { api, result } = await renderEnsureTool({ scenario: buildScenarioFixture({ mode: "master" }) });

    await act(() => result.current.ensureTool("atmosphere"));

    expect(api.toolPuts).toEqual([["atmosphere"]]);
    await waitFor(() =>
      expect(result.current.guide.scenario?.enabled_tools).toEqual(["status_hud", "atmosphere"]),
    );
  });

  it("keeps earlier tools when two are turned on at once", async () => {
    const { api, result } = await renderEnsureTool({ scenario: buildScenarioFixture({ mode: "master" }) });

    await act(async () => {
      await Promise.all([result.current.ensureTool("atmosphere"), result.current.ensureTool("composure")]);
    });

    expect(api.toolPuts).toEqual([["atmosphere"], ["status_hud", "atmosphere", "composure"]]);
  });

  it("refuses while Advanced mode is off and never calls the endpoint", async () => {
    const { api, result } = await renderEnsureTool({ scenario: buildScenarioFixture({ mode: "newbie" }) });

    await expect(result.current.ensureTool("composure")).rejects.toBeInstanceOf(ToolsRequireAdvancedModeError);
    expect(api.toolPuts).toEqual([]);
  });
});

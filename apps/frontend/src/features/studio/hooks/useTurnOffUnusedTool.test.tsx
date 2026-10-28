import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { useToastStore } from "@/shared/stores/toast.store";
import { useStudioTabsStore } from "../stores/studioTabs.store";
import { createGuideWrapper } from "../test/guideHookWrapper";
import {
  buildRuleCheckFixture,
  buildScenarioFixture,
  installStudioApi,
} from "../test/studioApiMock";
import { useGuide } from "./useGuide";
import { useRuleChecks } from "./useRuleChecks";
import { useTurnOffUnusedTool } from "./useTurnOffUnusedTool";

const renderRuleChecksTool = async (init: Parameters<typeof installStudioApi>[0]) => {
  const api = installStudioApi(init);
  const { Wrapper } = createGuideWrapper();
  const view = renderHook(
    () => ({ tool: useTurnOffUnusedTool("rule_checks"), checks: useRuleChecks("scenario-1"), guide: useGuide() }),
    { wrapper: Wrapper },
  );
  await waitFor(() => expect(view.result.current.checks.isLoading).toBe(false));
  await waitFor(() => expect(view.result.current.guide.scenario).not.toBeNull());
  return { api, ...view };
};

describe("useTurnOffUnusedTool", () => {
  beforeEach(() => {
    localStorage.clear();
    useStudioTabsStore.getState().resetTabs();
  });

  it("asks only after the last use is removed, then switches the tool off", async () => {
    const { api, result } = await renderRuleChecksTool({
      scenario: buildScenarioFixture({ mode: "master" }),
      enabledTools: ["rule_checks"],
      ruleChecks: [buildRuleCheckFixture({ check_id: "check-1" })],
    });
    expect(result.current.tool.shouldOffer).toBe(false);

    act(() => {
      result.current.checks.deleteCheck("check-1");
      result.current.tool.askAfterRemoval();
    });

    await waitFor(() => expect(result.current.tool.shouldOffer).toBe(true));
    expect(result.current.tool.question).toBe("Turn off Rule checks too?");
    await act(() => result.current.tool.confirm());
    expect(api.toolPuts).toEqual([[]]);
    await waitFor(() => expect(result.current.guide.scenario?.enabled_tools).toEqual([]));
    expect(result.current.tool.shouldOffer).toBe(false);
  });

  it("does not ask while another use remains", async () => {
    const { api, result } = await renderRuleChecksTool({
      scenario: buildScenarioFixture({ mode: "master" }),
      enabledTools: ["rule_checks"],
      ruleChecks: [buildRuleCheckFixture({ check_id: "check-1" }), buildRuleCheckFixture({ check_id: "check-2" })],
    });

    act(() => {
      result.current.checks.deleteCheck("check-1");
      result.current.tool.askAfterRemoval();
    });

    await waitFor(() => expect(api.ruleChecks).toHaveLength(1));
    await waitFor(() => expect(result.current.checks.checks).toHaveLength(1));
    expect(result.current.tool.shouldOffer).toBe(false);
  });

  it("tells the creator when another tool still needs the one being turned off", async () => {
    useToastStore.setState({ queue: [] });
    const api = installStudioApi({
      scenario: buildScenarioFixture({ mode: "master" }),
      enabledTools: ["status_hud", "atmosphere"],
    });
    const { Wrapper } = createGuideWrapper();
    const { result } = renderHook(() => ({ tool: useTurnOffUnusedTool("status_hud"), guide: useGuide() }), {
      wrapper: Wrapper,
    });
    await waitFor(() => expect(result.current.guide.scenario).not.toBeNull());

    await act(() => result.current.tool.confirm());

    expect(api.scenario?.enabled_tools).toEqual(["status_hud", "atmosphere"]);
    expect(useToastStore.getState().queue.map((item) => item.message)).toEqual([
      "Couldn't turn off Status HUD. Something still needs it.",
    ]);
  });

  it("stays quiet when the creator says no", async () => {
    const { result } = await renderRuleChecksTool({
      scenario: buildScenarioFixture({ mode: "master" }),
      enabledTools: ["rule_checks"],
      ruleChecks: [buildRuleCheckFixture({ check_id: "check-1" })],
    });
    act(() => {
      result.current.checks.deleteCheck("check-1");
      result.current.tool.askAfterRemoval();
    });
    await waitFor(() => expect(result.current.tool.shouldOffer).toBe(true));

    act(() => result.current.tool.dismiss());

    expect(result.current.tool.shouldOffer).toBe(false);
  });
});

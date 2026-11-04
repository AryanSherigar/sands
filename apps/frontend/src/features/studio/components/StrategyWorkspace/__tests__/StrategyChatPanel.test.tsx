import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { MapRegion } from "@/shared/types/strategy-map.types";
import { addFaction, readStrategyFields } from "../../../lib/strategyDocument";
import { StrategyChatPanel } from "../StrategyChatPanel";

const applier = { applyBatch: vi.fn() };
const useApplier = vi.fn((_args: unknown) => applier);
vi.mock("../../../hooks/useStrategyActionApplier", () => ({
  useStrategyActionApplier: (args: unknown) => useApplier(args),
}));

const drawerProps = vi.fn();
vi.mock("../../Layout/StudioChatDrawer", () => ({
  StudioChatDrawer: (props: unknown) => {
    drawerProps(props);
    return <div>chat drawer</div>;
  },
}));

const REGION: MapRegion = {
  id: "north",
  name: "North Reach",
  terrain: "plain",
  outline: "M0 0",
  label_point: { x: 1, y: 1 },
  neighbor_ids: [],
  source_color: null,
  source_ref: null,
};

describe("StrategyChatPanel", () => {
  beforeEach(() => {
    useApplier.mockClear();
    drawerProps.mockClear();
  });

  it("gives the drawer a context built from the open scenario and the applier", () => {
    const edit = vi.fn();
    render(
      <StrategyChatPanel
        scenarioId="scenario-1"
        title="The Reach"
        fields={addFaction(readStrategyFields({}), "Ashford")}
        mapRegions={[REGION]}
        activePanel="relations"
        edit={edit}
        isOpen
        onOpenChange={vi.fn()}
      />,
    );

    expect(screen.getByText("chat drawer")).toBeInTheDocument();
    const props = drawerProps.mock.calls[0][0] as { strategy: { context: { title: string; active_panel: string; factions: unknown[] }; applier: unknown } };
    expect(props.strategy.context).toMatchObject({ title: "The Reach", active_panel: "relations" });
    expect(props.strategy.context.factions).toHaveLength(1);
    expect(props.strategy.applier).toBe(applier);
  });

  it("lets the applier know which regions exist on the map", () => {
    render(
      <StrategyChatPanel
        scenarioId="scenario-1"
        title=""
        fields={readStrategyFields({})}
        mapRegions={[REGION]}
        activePanel={null}
        edit={vi.fn()}
        isOpen={false}
        onOpenChange={vi.fn()}
      />,
    );

    const args = useApplier.mock.calls[0][0] as { scenarioId: string; knownRegionIds: Set<string> };
    expect(args.scenarioId).toBe("scenario-1");
    expect([...args.knownRegionIds]).toEqual(["north"]);
  });
});

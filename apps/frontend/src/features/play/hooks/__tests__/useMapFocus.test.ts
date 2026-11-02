import { act, renderHook } from "@testing-library/react";
import type { ReactZoomPanPinchRef } from "react-zoom-pan-pinch";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { MapDocument } from "@/shared/types/strategy-map.types";
import { useStrategyPlayStore } from "../../stores/strategyPlay.store";
import { useMapFocus } from "../useMapFocus";

const MAP: MapDocument = {
  schema_version: 1,
  source: "manual",
  width: 1600,
  height: 900,
  image_url: "",
  roads: [],
  regions: [
    {
      id: "reg-a",
      name: "A",
      terrain: "plain",
      outline: "M 0 0 Z",
      label_point: { x: 800, y: 450 },
      neighbor_ids: [],
      source_color: null,
      source_ref: null,
    },
  ],
};

function fakeControls() {
  const setTransform = vi.fn();
  const controls = {
    setTransform,
    instance: { wrapperComponent: { offsetWidth: 1000, offsetHeight: 600 } },
  } as unknown as ReactZoomPanPinchRef;
  return { controls, setTransform };
}

describe("useMapFocus", () => {
  beforeEach(() => useStrategyPlayStore.getState().reset());

  it("pans the camera to the focused region", () => {
    const { controls, setTransform } = fakeControls();
    renderHook(() => useMapFocus(MAP, controls));

    act(() => useStrategyPlayStore.getState().focusMapLocation("reg-a"));

    expect(setTransform).toHaveBeenCalledWith(500 - 800 * 1.5, 300 - 450 * 1.5, 1.5, 300);
  });

  it("ignores unknown regions", () => {
    const { controls, setTransform } = fakeControls();
    renderHook(() => useMapFocus(MAP, controls));

    act(() => useStrategyPlayStore.getState().focusMapLocation("nope"));

    expect(setTransform).not.toHaveBeenCalled();
  });
});

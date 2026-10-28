import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { makeBlockImage, makeLabelMapFromRows } from "@/shared/lib/map-tracing/testImages";
import { traceLabelMap } from "@/shared/lib/map-tracing/traceLabelMap";
import type { MapDocument, PixelImage, TraceOptions } from "@/shared/types/strategy-map.types";
import { useRegionMapStore } from "../../stores/regionMap.store";
import { RegionMapEditor } from "./RegionMapEditor";

const PALETTE: Record<string, [number, number, number]> = {
  r: [255, 0, 0],
  g: [0, 160, 40],
  b: [0, 60, 250],
  w: [255, 255, 255],
  k: [0, 0, 0],
};
const CELL = 30;
const PICTURE_SIZE = { width: 60, height: 60 };

const mocks = vi.hoisted(() => ({
  pictureHolder: { pixels: null as PixelImage | null },
  failure: { shouldFail: false },
}));

vi.mock("../../hooks/useTraceMap", async () => {
  const { traceLabelMap: trace } = await import("@/shared/lib/map-tracing/traceLabelMap");
  const { buildLabelMap: build } = await import("@/shared/lib/map-tracing/buildLabelMap");
  const { makeBlockImage: blocks } = await import("@/shared/lib/map-tracing/testImages");
  const options: TraceOptions = { source: "color_image", imageUrl: null };
  const traceImage = async (image: PixelImage) => {
    const { labelMap, warnings } = build(image);
    return { labelMap, warnings, result: trace(labelMap, {}, options) };
  };
  const traceColorImage = async () => {
    if (mocks.failure.shouldFail) throw new Error("worker exploded");
    const image = blocks(
      ["rg", "bg"],
      { r: [255, 0, 0], g: [0, 160, 40], b: [0, 60, 250] },
      30,
    );
    return { ok: true as const, image, ...(await traceImage(image)) };
  };
  const retrace = async (map: never, meta: never, opts: TraceOptions) => trace(map, meta, opts);
  const stable = { traceImage, traceColorImage, retrace, isTracing: false };
  return { useTraceMap: () => stable };
});

vi.mock("../../hooks/usePicturePixels", () => ({
  usePicturePixels: () => ({ pixels: mocks.pictureHolder.pixels }),
}));

function renderEditor(props: Partial<{ initialDocument: MapDocument | null; onFinish: () => void }> = {}) {
  const onFinish = props.onFinish ?? vi.fn();
  render(
    <RegionMapEditor
      pictureUrl="data:image/png;base64,AAAA"
      pictureSize={PICTURE_SIZE}
      initialDocument={props.initialDocument ?? null}
      onFinish={onFinish}
    />,
  );
  return { onFinish };
}

async function traceFromColorImage(): Promise<void> {
  const user = userEvent.setup();
  await user.click(screen.getByRole("button", { name: /region-color image/i }));
  const file = new File(["x"], "regions.png", { type: "image/png" });
  await user.upload(screen.getByLabelText(/region color image/i), file);
  await screen.findByText(/regions found/i);
}

async function nameRegion(label: string, name: string, terrain: string): Promise<void> {
  const user = userEvent.setup();
  fireEvent.click(document.querySelector(`[data-region-id="${label}"]`) as Element);
  const input = screen.getByLabelText("Region name");
  await user.clear(input);
  await user.type(input, name);
  await user.selectOptions(screen.getByLabelText("Terrain"), terrain);
}

beforeEach(() => {
  useRegionMapStore.setState(useRegionMapStore.getInitialState(), true);
  mocks.pictureHolder.pixels = null;
  mocks.failure.shouldFail = false;
});

describe("RegionMapEditor", () => {
  it("shows what was traced and how many regions need attention", async () => {
    renderEditor();
    await traceFromColorImage();
    expect(screen.getByText("3 regions found, 3 need attention")).toBeInTheDocument();
  });

  it("selects a region when its problem is clicked", async () => {
    const user = userEvent.setup();
    renderEditor();
    await traceFromColorImage();
    await user.click(screen.getAllByRole("button", { name: /give this region a name/i })[0]);
    expect(screen.getByLabelText("Region name")).toHaveValue("");
  });

  it("enables Done once every region is named and has terrain", async () => {
    const user = userEvent.setup();
    const { onFinish } = renderEditor();
    await traceFromColorImage();
    expect(screen.getByRole("button", { name: "Done" })).toBeDisabled();
    await nameRegion("region_01", "Ashford", "hills");
    await nameRegion("region_02", "Brook", "forest");
    await nameRegion("region_03", "Coast", "coast");
    const done = screen.getByRole("button", { name: "Done" });
    await waitFor(() => expect(done).toBeEnabled());
    await user.click(done);
    expect(onFinish).toHaveBeenCalledTimes(1);
    const result = (onFinish as unknown as { mock: { calls: [{ document: MapDocument }][] } }).mock.calls[0][0];
    expect(result.document.regions.map((region) => region.name).sort()).toEqual(["Ashford", "Brook", "Coast"]);
  });

  it("keeps Done disabled and says why when the map has gaps", async () => {
    const map = makeLabelMapFromRows(["aaaa.bbbb"].flatMap((row) => Array(10).fill(row)));
    const { document } = traceLabelMap(map, {}, { source: "manual", imageUrl: null });
    renderEditor({ initialDocument: document });
    await screen.findByText(/regions found/i);
    expect(screen.getByRole("button", { name: "Done" })).toBeDisabled();
    expect(screen.getByText(/belong to no region/i)).toBeInTheDocument();
  });

  it("merges two regions and restores them on undo", async () => {
    const user = userEvent.setup();
    renderEditor();
    await traceFromColorImage();
    fireEvent.click(document.querySelector('[data-region-id="region_01"]') as Element);
    await user.click(screen.getByRole("button", { name: "Merge" }));
    fireEvent.click(document.querySelector('[data-region-id="region_02"]') as Element);
    await screen.findByText("2 regions found, 2 need attention");
    await user.click(screen.getByRole("button", { name: "Undo" }));
    await screen.findByText("3 regions found, 3 need attention");
  });

  it("applies one terrain to several selected regions", async () => {
    const user = userEvent.setup();
    renderEditor();
    await traceFromColorImage();
    fireEvent.click(document.querySelector('[data-region-id="region_01"]') as Element);
    fireEvent.click(document.querySelector('[data-region-id="region_02"]') as Element, { ctrlKey: true });
    await user.selectOptions(screen.getByLabelText("Terrain for selected"), "forest");
    fireEvent.click(document.querySelector('[data-region-id="region_02"]') as Element);
    expect(screen.getByLabelText("Terrain")).toHaveValue("forest");
  });

  it("starts hand-tracing empty and focuses the name box for a new region", async () => {
    const user = userEvent.setup();
    mocks.pictureHolder.pixels = makeBlockImage(["wk", "wk"], PALETTE, CELL);
    renderEditor();
    await user.click(screen.getByRole("button", { name: /trace by hand/i }));
    expect(await screen.findByText("0 regions found, 0 need attention")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Wand" }));
    const canvas = screen.getByLabelText("Region map");
    fireEvent.mouseDown(canvas, { clientX: 5, clientY: 5 });
    fireEvent.mouseUp(canvas, { clientX: 5, clientY: 5 });
    await screen.findByText("1 region found, 1 need attention");
    await waitFor(() => expect(screen.getByLabelText("Region name")).toHaveFocus());
    expect(within(screen.getByRole("list", { name: "Problems" })).getAllByRole("listitem").length).toBeGreaterThan(0);
  });

  it("starts from the chooser again after the editor is closed and reopened", async () => {
    const { unmount } = render(
      <RegionMapEditor
        pictureUrl="data:image/png;base64,AAAA"
        pictureSize={PICTURE_SIZE}
        initialDocument={null}
        onFinish={vi.fn()}
      />,
    );
    await traceFromColorImage();
    unmount();
    renderEditor();
    expect(screen.getByRole("button", { name: /region-color image/i })).toBeInTheDocument();
  });

  it("shows an error and stops the busy state when tracing fails", async () => {
    const user = userEvent.setup();
    mocks.failure.shouldFail = true;
    renderEditor();
    await user.click(screen.getByRole("button", { name: /region-color image/i }));
    const file = new File(["x"], "regions.png", { type: "image/png" });
    await user.upload(screen.getByLabelText(/region color image/i), file);
    expect(await screen.findByRole("alert")).toHaveTextContent(/could not trace/i);
    expect(screen.queryByText(/tracing the map/i)).not.toBeInTheDocument();
  });
});

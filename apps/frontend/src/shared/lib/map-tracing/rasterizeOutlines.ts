import type { LabelMap, MapDocument, Point } from "@/shared/types/strategy-map.types";

const SUPPORTED_COMMANDS = new Set(["M", "L", "Z"]);
const ID_SUFFIX = /_(\d+)$/;

function parseRings(outline: string): Point[][] {
  const tokens = outline.match(/[A-Za-z]|-?\d+/g) ?? [];
  const rings: Point[][] = [];
  let index = 0;
  while (index < tokens.length) {
    const command = tokens[index++];
    if (!SUPPORTED_COMMANDS.has(command)) {
      throw new Error(`Unsupported path command: ${command}`);
    }
    if (command === "Z") continue;
    const point = { x: Number(tokens[index++]), y: Number(tokens[index++]) };
    if (command === "M") rings.push([point]);
    else rings[rings.length - 1].push(point);
  }
  return rings;
}

export function crossingsAt(rings: Point[][], centreY: number): number[] {
  const crossings: number[] = [];
  for (const ring of rings) {
    ring.forEach((start, index) => {
      const end = ring[(index + 1) % ring.length];
      const isCrossing = Math.min(start.y, end.y) <= centreY && centreY < Math.max(start.y, end.y);
      if (!isCrossing) return;
      crossings.push(start.x + ((centreY - start.y) * (end.x - start.x)) / (end.y - start.y));
    });
  }
  return crossings.sort((first, second) => first - second);
}

function fillRegion(labels: Uint16Array, width: number, label: number, rings: Point[][], height: number): void {
  for (let y = 0; y < height; y++) {
    const crossings = crossingsAt(rings, y + 0.5);
    for (let pair = 0; pair + 1 < crossings.length; pair += 2) {
      const from = Math.max(0, Math.ceil(crossings[pair] - 0.5));
      const to = Math.min(width, Math.ceil(crossings[pair + 1] - 0.5));
      for (let x = from; x < to; x++) labels[y * width + x] = label;
    }
  }
}

function nextIdNumberFor(ids: string[]): number {
  const numbers = ids.map((id) => Number(ID_SUFFIX.exec(id)?.[1] ?? 0));
  return Math.max(ids.length, ...numbers) + 1;
}

export function rasterizeOutlines(document: MapDocument): LabelMap {
  const { width, height } = document;
  const labels = new Uint16Array(width * height);
  document.regions.forEach((region, index) => {
    fillRegion(labels, width, index + 1, parseRings(region.outline), height);
  });
  return {
    width,
    height,
    labels,
    entries: document.regions.map((region, index) => ({
      label: index + 1,
      id: region.id,
      sourceColor: region.source_color,
    })),
    nextIdNumber: nextIdNumberFor(document.regions.map((region) => region.id)),
  };
}

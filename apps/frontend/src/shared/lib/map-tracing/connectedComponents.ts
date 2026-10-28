export interface ComponentsResult {
  /** Component id per pixel; -1 for unassigned (label 0) pixels. */
  ids: Int32Array;
  sizes: number[];
  labelOf: number[];
}

const NO_COMPONENT = -1;

function neighbourIndexes(
  index: number,
  width: number,
  height: number,
): number[] {
  const x = index % width;
  const y = Math.floor(index / width);
  const result: number[] = [];
  if (x > 0) result.push(index - 1);
  if (x < width - 1) result.push(index + 1);
  if (y > 0) result.push(index - width);
  if (y < height - 1) result.push(index + width);
  return result;
}

function floodComponent(
  labels: Uint16Array,
  ids: Int32Array,
  start: number,
  componentId: number,
  size: { width: number; height: number },
): number {
  const stack = [start];
  ids[start] = componentId;
  let count = 0;
  while (stack.length > 0) {
    const index = stack.pop() as number;
    count++;
    for (const next of neighbourIndexes(index, size.width, size.height)) {
      if (ids[next] !== NO_COMPONENT || labels[next] !== labels[start]) continue;
      ids[next] = componentId;
      stack.push(next);
    }
  }
  return count;
}

export function connectedComponents(
  labels: Uint16Array,
  width: number,
  height: number,
): ComponentsResult {
  const ids = new Int32Array(labels.length).fill(NO_COMPONENT);
  const sizes: number[] = [];
  const labelOf: number[] = [];
  for (let index = 0; index < labels.length; index++) {
    if (labels[index] === 0 || ids[index] !== NO_COMPONENT) continue;
    const componentId = sizes.length;
    labelOf.push(labels[index]);
    sizes.push(floodComponent(labels, ids, index, componentId, { width, height }));
  }
  return { ids, sizes, labelOf };
}

export { neighbourIndexes };

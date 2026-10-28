export const moveItem = <T>(
  items: readonly T[],
  fromIndex: number,
  toIndex: number,
): T[] => {
  const isOutOfRange = (index: number): boolean =>
    index < 0 || index >= items.length;
  if (isOutOfRange(fromIndex) || isOutOfRange(toIndex)) return [...items];
  const next = [...items];
  const [moved] = next.splice(fromIndex, 1);
  next.splice(toIndex, 0, moved);
  return next;
};

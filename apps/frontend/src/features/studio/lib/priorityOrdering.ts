export const sortByPriority = <T extends { priority: number }>(
  items: T[],
): T[] => [...items].sort((a, b) => a.priority - b.priority);

export const reorderIds = (
  ids: string[],
  activeId: string,
  overId: string,
): string[] => {
  const activeIndex = ids.indexOf(activeId);
  const overIndex = ids.indexOf(overId);
  if (activeIndex === -1 || overIndex === -1) return ids;

  const reordered = [...ids];
  reordered.splice(activeIndex, 1);
  reordered.splice(overIndex, 0, activeId);
  return reordered;
};

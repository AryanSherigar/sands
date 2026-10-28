export const parseNextOffset = (page: {
  next_cursor: string | null;
}): number | undefined =>
  page.next_cursor === null ? undefined : Number(page.next_cursor);

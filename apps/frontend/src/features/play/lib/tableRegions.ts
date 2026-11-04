export interface TableRegion {
  id: string;
  name: string;
}

interface SituationFactLike {
  label: string;
  value: string;
}

const TABLE_REGIONS_LABEL = "Regions at the table";

const prettify = (id: string): string =>
  id
    .replace(/[-_]+/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());

export function parseTableRegions(facts: SituationFactLike[]): TableRegion[] {
  const fact = facts.find((item) => item.label === TABLE_REGIONS_LABEL);
  if (!fact) return [];
  return fact.value
    .split(",")
    .map((id) => id.trim())
    .filter((id) => id.length > 0)
    .map((id) => ({ id, name: prettify(id) }));
}

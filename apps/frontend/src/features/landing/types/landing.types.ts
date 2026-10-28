import type { GetScenariosParams } from "@/shared/types/scenarioSummary.types";

type LandingRowId = "for-you" | "top-rated" | "popular" | "new";

type DiscoverSort = "trending" | "popular" | "new";

export interface LandingRowConfig {
  id: LandingRowId;
  title: string;
  sort: NonNullable<GetScenariosParams["sort"]>;
  discoverSort: DiscoverSort;
}

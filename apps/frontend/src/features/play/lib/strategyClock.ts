import {
  MONTHS_PER_TURN,
  MONTHS_PER_YEAR,
  SEASON_BY_MONTH,
} from "../constants/strategy.constants";
import type { TurnClock } from "../types/simulation.types";

export interface StrategyDate {
  year: number;
  month: number;
  season: string;
}

export function deriveDate(clock: TurnClock, turnOffset = 0): StrategyDate {
  const elapsedMonths =
    clock.start_month - 1 + (clock.turn + turnOffset) * MONTHS_PER_TURN;
  const month = (elapsedMonths % MONTHS_PER_YEAR) + 1;
  const year = clock.start_year + Math.floor(elapsedMonths / MONTHS_PER_YEAR);
  return { year, month, season: SEASON_BY_MONTH[month - 1] };
}

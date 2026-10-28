import { useMemo } from "react";
import type { FactResponse } from "../types/fact.types";
import {
  countValueUsages,
  findLinkUsages,
  findValueUsages,
  type ValueUsages,
} from "../lib/valueOptions";

export type UsedIn = ValueUsages & { links: FactResponse[]; total: number };
import { useConditions } from "./useConditions";
import { useEndConditions } from "./useEndConditions";
import { useFacts } from "./useFacts";
import { useGuide } from "./useGuide";
import { useInvariants } from "./useInvariants";

export const useUsedIn = (path: string): UsedIn => {
  const { scenarioId } = useGuide();
  const { endConditions } = useEndConditions(scenarioId);
  const { conditions } = useConditions(scenarioId);
  const { invariants } = useInvariants(scenarioId);
  const { facts } = useFacts(scenarioId);

  return useMemo(() => {
    const usages = findValueUsages(path, { endConditions, conditions, invariants });
    const links = findLinkUsages(path, facts);
    return { ...usages, links, total: countValueUsages(usages) + links.length };
  }, [conditions, endConditions, facts, invariants, path]);
};

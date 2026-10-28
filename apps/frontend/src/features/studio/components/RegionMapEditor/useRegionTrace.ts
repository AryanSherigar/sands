import { useEffect, useRef, useState } from "react";
import { logEvent } from "@/shared/lib/logger";
import { downscaleLabelMap } from "@/shared/lib/map-tracing/editOps";
import type {
  LabelMap,
  RegionMeta,
  TraceOptions,
  TraceResult,
} from "@/shared/types/strategy-map.types";
import { PREVIEW_FACTOR } from "../../constants/regionMapEditor";

interface TraceSettings {
  source: "color_image" | "manual";
  imageUrl: string;
}

type Retrace = (
  labelMap: LabelMap,
  meta: Record<string, RegionMeta>,
  options: TraceOptions,
) => Promise<TraceResult>;

export function useRegionTrace(
  labelMap: LabelMap | null,
  settings: TraceSettings,
  retrace: Retrace,
) {
  const [draftMap, setDraftMap] = useState<LabelMap | null>(null);
  const [trace, setTrace] = useState<TraceResult | null>(null);
  const sequenceRef = useRef(0);

  useEffect(() => {
    if (!labelMap) {
      setTrace(null);
      return;
    }
    sequenceRef.current += 1;
    const sequence = sequenceRef.current;
    const target = draftMap ? downscaleLabelMap(draftMap, PREVIEW_FACTOR) : labelMap;
    retrace(target, {}, { source: settings.source, imageUrl: settings.imageUrl })
      .then((result) => {
        if (sequence === sequenceRef.current) setTrace(result);
      })
      .catch((error: unknown) => {
        logEvent("error", "region_map_trace_failed", {
          message: error instanceof Error ? error.message : "unknown",
        });
      });
  }, [labelMap, draftMap, retrace, settings.source, settings.imageUrl]);

  return { trace, draftMap, setDraftMap };
}

import type {
  TraceWorkerRequest,
  TraceWorkerResponse,
} from "@/shared/types/strategy-map.types";
import { buildLabelMap } from "./buildLabelMap";
import { traceLabelMap } from "./traceLabelMap";

function handle(request: TraceWorkerRequest): TraceWorkerResponse {
  if (request.type === "trace-map") {
    const result = traceLabelMap(request.labelMap, request.meta, request.options);
    return { type: "done-map", result };
  }
  const { labelMap, warnings } = buildLabelMap(request.image, request.extraSeeds);
  const result = traceLabelMap(labelMap, {}, request.options);
  return { type: "done-image", labelMap, warnings, result };
}

self.onmessage = (event: MessageEvent<TraceWorkerRequest>): void => {
  try {
    self.postMessage(handle(event.data));
  } catch (error) {
    const message = error instanceof Error ? error.message : "Tracing failed";
    self.postMessage({ type: "error", message } satisfies TraceWorkerResponse);
  }
};

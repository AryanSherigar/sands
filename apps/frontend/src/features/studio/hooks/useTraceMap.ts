import { useCallback, useEffect, useRef, useState } from "react";
import { validateRegionImageFile } from "@/shared/lib/map-tracing/decodeImage";
import type {
  LabelMap,
  PixelImage,
  RegionImageRejection,
  RegionMeta,
  TraceOptions,
  TraceResult,
  TraceWarning,
  TraceWorkerRequest,
  TraceWorkerResponse,
} from "@/shared/types/strategy-map.types";

type Waiter = {
  resolve: (response: TraceWorkerResponse) => void;
  reject: (error: Error) => void;
};

export interface ImageTrace {
  labelMap: LabelMap;
  warnings: TraceWarning[];
  result: TraceResult;
}

export type TraceOutcome =
  | ({ ok: true; image: PixelImage } & ImageTrace)
  | { ok: false; reason: RegionImageRejection };

const COLOR_IMAGE_OPTIONS: TraceOptions = { source: "color_image", imageUrl: null };

function createWorker(): Worker {
  return new Worker(
    new URL("../../../shared/lib/map-tracing/trace.worker.ts", import.meta.url),
    { type: "module" },
  );
}

export function useTraceMap() {
  const workerRef = useRef<Worker | null>(null);
  const waitersRef = useRef<Waiter[]>([]);
  const [pendingCount, setPendingCount] = useState(0);

  const getWorker = useCallback((): Worker => {
    if (workerRef.current) return workerRef.current;
    const worker = createWorker();
    worker.onmessage = (event: MessageEvent<TraceWorkerResponse>): void => {
      if (event.data.type === "progress") return;
      const waiter = waitersRef.current.shift();
      setPendingCount((count) => count - 1);
      if (event.data.type === "error") waiter?.reject(new Error(event.data.message));
      else waiter?.resolve(event.data);
    };
    worker.onerror = (): void => {
      const waiters = waitersRef.current.splice(0);
      setPendingCount(0);
      workerRef.current?.terminate();
      workerRef.current = null;
      waiters.forEach((waiter) => waiter.reject(new Error("The trace worker crashed")));
    };
    workerRef.current = worker;
    return worker;
  }, []);

  useEffect(() => () => workerRef.current?.terminate(), []);

  const send = useCallback(
    (request: TraceWorkerRequest): Promise<TraceWorkerResponse> =>
      new Promise((resolve, reject) => {
        waitersRef.current.push({ resolve, reject });
        setPendingCount((count) => count + 1);
        getWorker().postMessage(request);
      }),
    [getWorker],
  );

  const traceImage = useCallback(
    async (image: PixelImage, extraSeeds: [number, number, number][] = []): Promise<ImageTrace> => {
      const response = await send({ type: "trace-image", image, extraSeeds, options: COLOR_IMAGE_OPTIONS });
      if (response.type !== "done-image") throw new Error("Unexpected worker response");
      return { labelMap: response.labelMap, warnings: response.warnings, result: response.result };
    },
    [send],
  );

  const retrace = useCallback(
    async (labelMap: LabelMap, meta: Record<string, RegionMeta>, options: TraceOptions): Promise<TraceResult> => {
      const response = await send({ type: "trace-map", labelMap, meta, options });
      if (response.type !== "done-map") throw new Error("Unexpected worker response");
      return response.result;
    },
    [send],
  );

  const traceColorImage = useCallback(
    async (file: File, pictureSize: { width: number; height: number }): Promise<TraceOutcome> => {
      const validation = await validateRegionImageFile(file, pictureSize);
      if (!validation.ok) return validation;
      return { ok: true, image: validation.image, ...(await traceImage(validation.image)) };
    },
    [traceImage],
  );

  return { traceColorImage, traceImage, retrace, isTracing: pendingCount > 0 };
}

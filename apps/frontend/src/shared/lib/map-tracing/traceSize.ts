import { MAX_TRACE_SIDE } from "@/shared/constants/mapTracing";

export interface Size {
  width: number;
  height: number;
}

export function fitToTraceSide(size: Size): Size {
  const scale = Math.min(1, MAX_TRACE_SIDE / Math.max(size.width, size.height));
  return {
    width: Math.max(1, Math.round(size.width * scale)),
    height: Math.max(1, Math.round(size.height * scale)),
  };
}

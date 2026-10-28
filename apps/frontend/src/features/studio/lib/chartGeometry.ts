import {
  BAR_LIST_LABEL_WIDTH,
  BAR_LIST_VALUE_WIDTH,
  BAR_WIDTH_RATIO,
  CHART_GRIDLINE_COUNT,
  CHART_HEIGHT,
  CHART_LABEL_GUTTER,
  CHART_PADDING,
  CHART_WIDTH,
  HEATMAP_MIN_OPACITY,
} from "../constants/stats";
import type { ChartDatum } from "../types/statsView.types";

export interface PlottedPoint {
  x: number;
  y: number;
  datum: ChartDatum;
}

export interface PlottedBar {
  x: number;
  y: number;
  width: number;
  height: number;
  datum: ChartDatum;
}

const maxValue = (data: ChartDatum[]): number =>
  Math.max(1, ...data.map((datum) => datum.value));

export const plotPoints = (data: ChartDatum[]): PlottedPoint[] => {
  const innerWidth = CHART_WIDTH - CHART_PADDING * 2;
  const innerHeight = CHART_HEIGHT - CHART_PADDING * 2;
  const step = data.length > 1 ? innerWidth / (data.length - 1) : 0;
  const peak = maxValue(data);
  return data.map((datum, index) => ({
    x: CHART_PADDING + index * step,
    y: CHART_PADDING + innerHeight - (datum.value / peak) * innerHeight,
    datum,
  }));
};

export const plotBars = (data: ChartDatum[]): PlottedBar[] => {
  const innerWidth = CHART_WIDTH - CHART_PADDING * 2;
  const innerHeight = CHART_HEIGHT - CHART_PADDING - CHART_LABEL_GUTTER;
  const slot = data.length > 0 ? innerWidth / data.length : 0;
  const width = slot * BAR_WIDTH_RATIO;
  const peak = maxValue(data);
  return data.map((datum, index) => {
    const height = (datum.value / peak) * innerHeight;
    return {
      x: CHART_PADDING + index * slot + (slot - width) / 2,
      y: CHART_PADDING + innerHeight - height,
      width,
      height,
      datum,
    };
  });
};

export const gridlineOffsets = (bottom: number): number[] => {
  const spacing = (bottom - CHART_PADDING) / CHART_GRIDLINE_COUNT;
  return Array.from(
    { length: CHART_GRIDLINE_COUNT + 1 },
    (_, index) => CHART_PADDING + spacing * index,
  );
};

export const barListWidth = (fraction: number): number => {
  const clamped = Math.min(1, Math.max(0, fraction));
  return clamped * (CHART_WIDTH - BAR_LIST_LABEL_WIDTH - BAR_LIST_VALUE_WIDTH);
};

export const pinOpacity = (discoveryRate: number | null): number => {
  if (discoveryRate === null) return HEATMAP_MIN_OPACITY;
  const clamped = Math.min(1, Math.max(0, discoveryRate));
  return HEATMAP_MIN_OPACITY + (1 - HEATMAP_MIN_OPACITY) * clamped;
};

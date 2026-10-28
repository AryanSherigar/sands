import type { MapDocument } from "@/shared/types/strategy-map.types";

export const FALLBACK_STRATEGY_MAP: MapDocument = {
  schema_version: 1,
  source: "manual",
  width: 1600,
  height: 900,
  image_url:
    "https://lh3.googleusercontent.com/aida/AEtjO1XiwZoEAVB5Car35_06iCD25KBtRBUDPKGOuN_4SGl60ujVzikg-X6qX3rrUvheVEotFcvzjjjRnzL0AL1eJ87vJCOHFPwQHgHkLhJ3NXQHd96pbsq6Uh1bpD9sridDLOoFk9uLf02Ucir9jjIu1SsbPV0pikQCIEKu3TjhWtzkGrkX0zyUX5pfJ40c7DFLEGr6M8N42d1TZWc6PDcK0XffJcYVTHTK7DTl6RR1AsA6U23_YBf2E3Y7PhUV",
  regions: [
    {
      id: "reg-dunmere",
      name: "Dunmere Vale",
      terrain: "plain",
      outline: "M 650 350 C 750 320 850 380 830 500 C 800 600 680 580 650 500 Z",
      label_point: { x: 780, y: 430 },
      neighbor_ids: ["reg-greenford", "reg-highcrag", "reg-silverwood"],
      source_color: null,
      source_ref: null,
    },
    {
      id: "reg-greenford",
      name: "Greenford Shire",
      terrain: "forest",
      outline: "M 480 440 C 580 430 650 500 600 600 C 500 620 450 520 480 440 Z",
      label_point: { x: 540, y: 490 },
      neighbor_ids: ["reg-dunmere"],
      source_color: null,
      source_ref: null,
    },
    {
      id: "reg-highcrag",
      name: "High Crag Keep",
      terrain: "mountain",
      outline: "M 1100 200 C 1220 180 1280 300 1220 380 C 1140 370 1080 290 1100 200 Z",
      label_point: { x: 1170, y: 250 },
      neighbor_ids: ["reg-dunmere"],
      source_color: null,
      source_ref: null,
    },
    {
      id: "reg-silverwood",
      name: "Silverwood Hold",
      terrain: "coast",
      outline: "M 320 300 C 420 280 450 400 380 460 C 290 450 280 360 320 300 Z",
      label_point: { x: 370, y: 340 },
      neighbor_ids: ["reg-dunmere"],
      source_color: null,
      source_ref: null,
    },
  ],
  roads: [
    { region_a: "reg-dunmere", region_b: "reg-greenford" },
    { region_a: "reg-dunmere", region_b: "reg-highcrag" },
    { region_a: "reg-dunmere", region_b: "reg-silverwood" },
  ],
};

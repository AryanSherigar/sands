export interface MapPictureSize {
  width: number;
  height: number;
}

export interface GeneratedRegionImage {
  region_image_url: string;
  width: number;
  height: number;
}

export interface GeneratedMapArt {
  picture_url: string;
  width: number;
  height: number;
}

export interface GeneratedMap {
  picture: { url: string; size: MapPictureSize };
  regionImage: File;
  hasArt: boolean;
}

export type GenerateMapStage = "idle" | "regions" | "art";

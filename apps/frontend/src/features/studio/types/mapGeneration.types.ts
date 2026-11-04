export interface MapPictureSize {
  width: number;
  height: number;
}

export type MapGenerationJobStatus = "pending" | "running" | "succeeded" | "failed";

export interface MapGenerationJob {
  job_id: string;
  scenario_id: string;
  status: MapGenerationJobStatus;
  description: string;
  region_image_url: string | null;
  picture_url: string | null;
  width: number | null;
  height: number | null;
  has_art: boolean;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface GeneratedMap {
  picture: { url: string; size: MapPictureSize };
  regionImage: File;
  hasArt: boolean;
}

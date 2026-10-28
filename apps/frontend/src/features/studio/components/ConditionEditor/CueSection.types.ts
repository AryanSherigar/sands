interface CueSectionValue {
  cue: string;
  cutAmbient: boolean;
  silenceMs: number;
}

export interface CueSectionProps {
  value: CueSectionValue;
  onChange: (value: CueSectionValue) => void;
  onPreview?: (cue: string) => Promise<"played" | "blocked">;
}

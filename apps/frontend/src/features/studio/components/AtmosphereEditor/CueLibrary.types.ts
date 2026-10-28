export interface CueLibraryProps {
  onPreview?: (cue: string) => Promise<"played" | "blocked">;
}

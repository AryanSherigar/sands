import type { TreatyVerdict } from "../../../../types/scene.types";

export interface VerdictNoteProps {
  verdict: TreatyVerdict | null | undefined;
  hasProposal: boolean;
}

import { STYLE_CHIP_QUESTION_PREFIX, type StyleChip } from "../constants/styleChips";
import type { LoreDocument } from "../types/lore.types";
import { getAnswer, setAnswer } from "./loreDocument";

const toQuestion = (chip: StyleChip) => ({
  id: `${STYLE_CHIP_QUESTION_PREFIX}${chip.id}`,
  label: chip.label,
});

export const isStyleChipOn = (document: LoreDocument, chip: StyleChip): boolean =>
  getAnswer(document, toQuestion(chip).id).trim().length > 0;

export const toggleStyleChip = (
  document: LoreDocument,
  chip: StyleChip,
): LoreDocument =>
  setAnswer(document, toQuestion(chip), isStyleChipOn(document, chip) ? "" : chip.wording);

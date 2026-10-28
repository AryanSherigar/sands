import type { StateFieldOption } from "../../types/scenario.types";

export interface RandomInitialPickerProps {
  options: StateFieldOption[] | undefined;
  value: string[] | undefined;
  onChange: (value: string[] | undefined) => void;
}

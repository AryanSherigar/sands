import type { StateFieldOption } from "../../types/scenario.types";

export interface EnumOptionsInputProps {
  options: StateFieldOption[] | undefined;
  onChange: (options: StateFieldOption[]) => void;
}

import { AvailableField } from "../ConditionEditor/ExpressionBuilder/ExpressionBuilder.types";
import { MinigameCreate, MinigameResponse } from "../../types/minigame.types";

export interface MinigameFormProps {
  availableFields: AvailableField[];
  minigame?: MinigameResponse | null;
  onSubmit: (payload: MinigameCreate) => void;
  onCancel: () => void;
  isComposureEnabled?: boolean;
  isSubmitting: boolean;
  submitError: string | null;
}

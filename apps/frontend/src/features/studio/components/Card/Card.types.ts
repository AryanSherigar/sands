import type { AttributeFieldSchema, EntityResponse } from "../../types/entity.types";
import type { QuestionGroup } from "../../types/guide.types";

export interface CardProps {
  scenarioId: string;
  entityId: string;
  questions?: QuestionGroup[];
  typeLabel?: string;
  onOpenCard?: (entityId: string) => void;
  onDeleted?: (entityId: string) => void;
  onAddToAlwaysRemember?: (line: string) => void;
}

export interface TriggerChipsProps {
  name: string;
  triggers: string[];
  onAdd: (trigger: string) => void;
  onRemove: (trigger: string) => void;
}

export interface CardMenuProps {
  name: string;
  onOpenInTab?: () => void;
  onDuplicate: () => void;
  onDelete: () => void;
}

export interface DeleteCardDialogProps {
  isOpen: boolean;
  cardName: string;
  linkSentences: string[];
  isDeleting: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export interface CardValuesProps {
  scenarioId: string;
  entity: EntityResponse;
}

export interface CardValueCardProps {
  entityId: string;
  valueKey: string;
  attribute: AttributeFieldSchema;
  onChange: (next: AttributeFieldSchema) => void;
  onDelete: () => void;
}

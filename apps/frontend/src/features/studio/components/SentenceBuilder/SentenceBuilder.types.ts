import type { FieldExpression } from "../ConditionEditor/ExpressionBuilder/ExpressionBuilder.types";
import type { DraftRow, DraftRowInput, SentenceBuilderMode, SentenceOutput } from "../../lib/sentenceRows";
import type { SentenceMetadata, SentenceJoiner, ValueOption } from "../../types/sentence.types";
import type { NewValueForm } from "../../hooks/useNewValueForm";

export interface SentenceBuilderProps {
  value: FieldExpression | null;
  metadata?: SentenceMetadata;
  onChange: (next: SentenceOutput | null) => void;
  onOpenFullEditor?: () => void;
  onValidityChange?: (isValid: boolean) => void;
  mode?: SentenceBuilderMode;
  scopeFilter?: (option: ValueOption) => boolean;
  canCompareToValue?: boolean;
  maxRows?: number;
}

export interface ValuePickerProps {
  path: string;
  options: ValueOption[];
  missingName: string | null;
  label: string;
  onSelect: (path: string) => void;
  onRequestNew: () => void;
}

export interface AmountFieldProps {
  row: DraftRow;
  option: ValueOption;
  numberOptions: ValueOption[];
  onChange: (next: DraftRowInput) => void;
}

export interface SentenceRowProps {
  row: DraftRow;
  options: ValueOption[];
  allOptions: ValueOption[];
  rowLabel: string;
  leadLabel?: string;
  missingName: string | null;
  isMustRow?: boolean;
  canCompareToValue?: boolean;
  onChange: (next: DraftRowInput) => void;
  onRemove?: () => void;
  onRequestNew: () => void;
}

export interface NewValueInlineProps {
  onCreated: (option: ValueOption) => void;
  onCancel: () => void;
}

export interface JoinerPickerProps {
  joiner: SentenceJoiner;
  onChange: (joiner: SentenceJoiner) => void;
}

export interface SentencePreviewProps {
  text: string;
}

export interface AdvancedLogicNoticeProps {
  onOpenFullEditor?: () => void;
}

export interface NewValueFieldsProps {
  form: NewValueForm;
}

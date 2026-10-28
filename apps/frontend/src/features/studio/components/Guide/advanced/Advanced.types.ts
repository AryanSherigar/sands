import type { CSSProperties, ReactNode, Ref } from "react";
import type { MeterTier } from "@/shared/types/display-hints.types";
import type { HudAvailability } from "../../../lib/trackedValueEditing";
import type { EndConditionResponse, EndConditionUpdate } from "../../../types/end_condition.types";
import type { ChangeRow } from "../../../lib/changeRows";
import type { RuleDraft, SoundDraft } from "../../../lib/ruleDraft";
import type { ConditionResponse, ConditionUpdate } from "../../../types/condition.types";
import type { InvariantResponse, InvariantUpdate } from "../../../types/invariant.types";
import type { FieldExpression } from "../../ConditionEditor/ExpressionBuilder/ExpressionBuilder.types";
import type { SentenceMetadata, ValueOption } from "../../../types/sentence.types";
import type { StateFieldDefinition } from "../../../types/scenario.types";
import type { NewTrackedValue } from "../../../types/trackedValue.types";
import type { TurnOffUnusedTool } from "../../../hooks/useTurnOffUnusedTool";
import type { ExtraDefinition, ExtraRemoval } from "../../../constants/extras";
import type { OverflowMenuItem } from "@/shared/components/ui/OverflowMenu.types";

export interface AdvancedCardProps {
  ariaLabel: string;
  badge: string;
  menuLabel: string;
  menuItems: OverflowMenuItem[];
  leading?: ReactNode;
  cardRef?: Ref<HTMLElement>;
  style?: CSSProperties;
  children: ReactNode;
}

export interface TurnOffToolPromptProps {
  tool: TurnOffUnusedTool;
}

export interface ExampleChipsProps {
  heading: string;
  examples: ReadonlyArray<{ id: string; label: string }>;
  onPick: (exampleId: string) => void;
}

export interface FieldBlockProps {
  label: string;
  helper?: string;
  children: ReactNode;
}

export interface NumberFieldProps {
  label: string;
  value: number | undefined;
  placeholder?: string;
  onChange: (value: number | undefined) => void;
  onBlur?: () => void;
}

export interface TrackedValueCardProps {
  valueKey: string;
  field: StateFieldDefinition;
  availability: HudAvailability;
  onChange: (next: StateFieldDefinition) => void;
  onDelete: () => void;
}

export interface TrackedValueFieldsProps {
  field: StateFieldDefinition;
  onChange: (next: StateFieldDefinition) => void;
}

export interface PlayerSeesFieldsProps {
  field: StateFieldDefinition;
  availability: HudAvailability;
  onChange: (next: StateFieldDefinition) => void;
}

export interface LevelsEditorProps {
  tiers: MeterTier[];
  onChange: (tiers: MeterTier[]) => void;
}

export interface UsedInListProps {
  valueKey: string;
}

export interface HudPreviewStripProps {
  schema: Record<string, StateFieldDefinition>;
}

export interface ValueQuickAddProps {
  existingLabels: ReadonlySet<string>;
  onAdd: (input: NewTrackedValue) => void;
}

export interface ComparisonFitNoteProps {
  expression: FieldExpression | null;
  metadata: SentenceMetadata | undefined;
  options: ValueOption[];
}

export interface DeleteValueDialogProps {
  isOpen: boolean;
  title?: string;
  confirmLabel?: string;
  question: string;
  onConfirm: () => void;
  onCancel: () => void;
}

export interface EndingCardProps {
  ending: EndConditionResponse;
  index: number;
  count: number;
  onUpdate: (patch: EndConditionUpdate) => void;
  onDuplicate: () => void;
  onDelete: () => void;
  onMove: (offset: -1 | 1) => void;
}

export interface ChangeRowFieldsProps {
  row: ChangeRow;
  rowLabel: string;
  options: ValueOption[];
  onChange: (next: ChangeRow) => void;
  onRemove: () => void;
}

export interface ThenActionsProps {
  draft: RuleDraft;
  options: ValueOption[];
  onChange: (next: RuleDraft) => void;
  onSoundChange: (next: SoundDraft) => void;
}

export interface RuleCardProps {
  rule: ConditionResponse;
  index: number;
  onUpdate: (patch: ConditionUpdate) => void;
  onDuplicate: () => void;
  onDelete: () => void;
  onSoundRemoved: () => void;
}

export interface HardLimitCardProps {
  limit: InvariantResponse;
  index: number;
  onUpdate: (patch: InvariantUpdate) => void;
  onDuplicate: () => void;
  onDelete: () => void;
}

export interface ExtraCardProps {
  extra: ExtraDefinition;
  isOn: boolean;
  removal: ExtraRemoval | null;
  onAdd: () => void;
  onEdit: () => void;
  onRemove: () => void;
}

export interface ChangeAmountInputProps {
  row: ChangeRow;
  option: ValueOption;
  onChange: (value: ChangeRow["value"]) => void;
}

export interface ClockFieldsProps {
  field: StateFieldDefinition;
  onChange: (next: StateFieldDefinition) => void;
}

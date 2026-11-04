import {
  GATE_KINDS,
  KIND_LABELS,
  MAX_EXPIRY_TURNS,
  MIN_EXPIRY_TURNS,
  TEMPLATE_LABELS,
  isRegionKind,
  isRegionTemplate,
  type ClauseKind,
  type ClauseMode,
  type ClauseSubject,
  type ClauseTemplate,
} from "../../../../lib/clauseSentence";
import { FORM_INPUT_CLASS, FormField } from "../../ui/FormField";
import type { ClauseDraftFieldsProps } from "./ClauseDraftFields.types";

const NEEDS_AMOUNT: ClauseKind[] = ["payment", "tribute", "pact"];
const AMOUNT_LABELS: Partial<Record<ClauseKind, string>> = { payment: "Gold", tribute: "Percent of income", pact: "Turns" };
const NEVER_GATED: ClauseKind[] = ["payment", "cede_region"];

export function ClauseDraftFields({ draft, position, regions, canRemove, onChange, onRemove }: ClauseDraftFieldsProps) {
  const hasRegions = regions.length > 0;
  const isConditional = draft.mode !== "none";
  const kinds = (Object.keys(KIND_LABELS) as ClauseKind[]).filter(
    (kind) => (hasRegions || !isRegionKind(kind)) && (draft.mode !== "gate" || GATE_KINDS.includes(kind)),
  );
  const templates = (Object.keys(TEMPLATE_LABELS) as ClauseTemplate[]).filter(
    (template) => hasRegions || !isRegionTemplate(template),
  );
  const needsRegion = isRegionKind(draft.kind) || (isConditional && isRegionTemplate(draft.template));

  const handleModeChange = (mode: ClauseMode): void => {
    const keepsKind = mode !== "gate" || !NEVER_GATED.includes(draft.kind);
    onChange({ mode, kind: keepsKind ? draft.kind : "pact" });
  };
  const handleRegionChange = (regionId: string): void =>
    onChange({ regionId, regionName: regions.find((region) => region.id === regionId)?.name });

  return (
    <fieldset className="space-y-3 border border-outline-variant/30 rounded-lg p-3">
      <legend className="px-1 font-sans text-xs font-semibold text-outline">Clause {position}</legend>
      <FormField label="When it applies">
        <select className={FORM_INPUT_CLASS} value={draft.mode} onChange={(event) => handleModeChange(event.target.value as ClauseMode)}>
          <option value="none">Straight away</option>
          <option value="trigger">Once a condition is met, it begins</option>
          <option value="gate">It holds only while a condition is true</option>
        </select>
      </FormField>
      <FormField label="The clause">
        <select className={FORM_INPUT_CLASS} value={draft.kind} onChange={(event) => onChange({ kind: event.target.value as ClauseKind })}>
          {kinds.map((kind) => (
            <option key={kind} value={kind}>{KIND_LABELS[kind]}</option>
          ))}
        </select>
      </FormField>
      {NEEDS_AMOUNT.includes(draft.kind) ? (
        <FormField label={AMOUNT_LABELS[draft.kind] ?? "Amount"}>
          <input className={FORM_INPUT_CLASS} type="number" min={1} value={draft.amount} onChange={(event) => onChange({ amount: Number(event.target.value) })} />
        </FormField>
      ) : null}
      {isConditional ? (
        <>
          <FormField label="Condition">
            <select className={FORM_INPUT_CLASS} value={draft.template} onChange={(event) => onChange({ template: event.target.value as ClauseTemplate })}>
              {templates.map((template) => (
                <option key={template} value={template}>{TEMPLATE_LABELS[template]}</option>
              ))}
            </select>
          </FormField>
          {draft.template !== "turn_after" ? (
            <FormField label="Whose">
              <select className={FORM_INPUT_CLASS} value={draft.subject} onChange={(event) => onChange({ subject: event.target.value as ClauseSubject })}>
                <option value="mine">Mine</option>
                <option value="yours">Theirs</option>
              </select>
            </FormField>
          ) : null}
          {!isRegionTemplate(draft.template) ? (
            <FormField label="Value">
              <input className={FORM_INPUT_CLASS} type="number" min={0} value={draft.value} onChange={(event) => onChange({ value: Number(event.target.value) })} />
            </FormField>
          ) : null}
          <FormField label={`Lapses after (${MIN_EXPIRY_TURNS} to ${MAX_EXPIRY_TURNS} turns)`}>
            <input className={FORM_INPUT_CLASS} type="number" min={MIN_EXPIRY_TURNS} max={MAX_EXPIRY_TURNS} value={draft.expiresInTurns} onChange={(event) => onChange({ expiresInTurns: Number(event.target.value) })} />
          </FormField>
        </>
      ) : null}
      {needsRegion ? (
        <FormField label="Region">
          <select className={FORM_INPUT_CLASS} value={draft.regionId ?? ""} onChange={(event) => handleRegionChange(event.target.value)}>
            <option value="" disabled>Choose a region</option>
            {regions.map((region) => (
              <option key={region.id} value={region.id}>{region.name}</option>
            ))}
          </select>
        </FormField>
      ) : null}
      {canRemove ? (
        <button type="button" onClick={onRemove} className="font-sans text-xs text-tertiary hover:underline cursor-pointer">
          Remove this clause
        </button>
      ) : null}
    </fieldset>
  );
}

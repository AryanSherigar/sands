import React, { useState } from "react";
import { NAME_SETUP_FIELD, SETUP_QUICK_ADDS } from "../../constants/guideChips";
import { useGuide } from "../../hooks/useGuide";
import { useSyncedValue } from "../../hooks/useSyncedValue";
import {
  buildCustomField,
  buildQuickAddField,
  hasNameField,
  hasQuickAdd,
  removeField,
  updateField,
} from "../../lib/setupFields";
import { GuideChip } from "./GuideChip";
import { SetupFieldRow } from "./SetupFieldRow";
import { SetupPreview } from "./SetupPreview";

const DEFAULT_FIELDS = [NAME_SETUP_FIELD];

export const SetupFieldsSection: React.FC = () => {
  const { scenario, saveFields } = useGuide();
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);
  const { value: fields, commit } = useSyncedValue(
    scenario ? scenario.setup_schema : DEFAULT_FIELDS,
    (next) => saveFields({ setup_schema: next }),
  );
  const missingQuickAdds = SETUP_QUICK_ADDS.filter((chip) => !hasQuickAdd(fields, chip));

  return (
    <section aria-labelledby="setup-choices" className="space-y-3">
      <h3 id="setup-choices" className="text-heading font-semibold text-content">
        What can players choose before they start?
      </h3>
      <ul className="space-y-2">
        {fields.map((field) => (
          <SetupFieldRow
            key={field.id}
            field={field}
            onChange={(updates) => commit(updateField(fields, field.id, updates))}
            onRemove={() => commit(removeField(fields, field.id))}
          />
        ))}
      </ul>
      <div className="flex flex-wrap gap-2">
        {!hasNameField(fields) && (
          <GuideChip
            label="+ Name"
            onClick={() => commit([NAME_SETUP_FIELD, ...fields])}
          />
        )}
        {missingQuickAdds.map((chip) => (
          <GuideChip
            key={chip.id}
            label={`+ ${chip.label}`}
            onClick={() => commit([...fields, buildQuickAddField(chip, fields)])}
          />
        ))}
        <GuideChip
          label="+ Your own…"
          onClick={() => commit([...fields, buildCustomField(fields)])}
        />
      </div>
      <button
        type="button"
        aria-expanded={isPreviewOpen}
        onClick={() => setIsPreviewOpen((current) => !current)}
        className="text-meta font-medium text-content-muted underline underline-offset-4 hover:text-content"
      >
        {isPreviewOpen ? "Hide the Setup screen" : "Preview the Setup screen"}
      </button>
      {isPreviewOpen && <SetupPreview fields={fields} />}
    </section>
  );
};

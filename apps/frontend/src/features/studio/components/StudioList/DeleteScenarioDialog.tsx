import React, { useEffect, useState } from "react";
import { Button } from "@/shared/components/ui/Button";
import { Input } from "@/shared/components/ui/Input";
import { Modal } from "@/shared/components/ui/Modal";
import { UNTITLED_SCENARIO_TITLE } from "../../constants/studio-list";
import {
  getDeleteOutcome,
  isTitleConfirmed,
} from "../../utils/scenarioRowStatus";
import type { DeleteScenarioDialogProps } from "./StudioList.types";

const OUTCOME_COPY = {
  deleted:
    "This permanently deletes the scenario and everything in it. If it has playthroughs it is archived instead.",
  archived:
    "This scenario has been published. Deleting it archives it and hides it from players. Playthroughs and reviews are kept.",
} as const;

export const DeleteScenarioDialog: React.FC<DeleteScenarioDialogProps> = ({
  scenario,
  onClose,
  onConfirm,
}) => {
  const [typedTitle, setTypedTitle] = useState("");
  const scenarioId = scenario?.scenario_id;

  useEffect(() => setTypedTitle(""), [scenarioId]);

  if (!scenario) return null;
  const displayTitle = scenario.title.trim() || UNTITLED_SCENARIO_TITLE;
  const canConfirm = isTitleConfirmed(
    typedTitle,
    scenario.title,
    UNTITLED_SCENARIO_TITLE,
  );
  const outcome = getDeleteOutcome(scenario);

  return (
    <Modal isOpen onClose={onClose} title={`Delete “${displayTitle}”?`}>
      <p className="font-sans text-sm text-content-muted">
        {OUTCOME_COPY[outcome]}
      </p>
      <label className="mt-4 block font-sans text-xs text-content-faint">
        To confirm, type{" "}
        <span className="font-mono text-content">{displayTitle}</span> below
        <Input
          className="mt-1"
          value={typedTitle}
          onChange={(event) => setTypedTitle(event.target.value)}
          autoComplete="off"
        />
      </label>
      <div className="mt-4 flex justify-end gap-2">
        <Button variant="secondary" onClick={onClose}>
          Cancel
        </Button>
        <Button
          variant="danger"
          disabled={!canConfirm}
          onClick={() => onConfirm(scenario)}
        >
          Delete scenario
        </Button>
      </div>
    </Modal>
  );
};

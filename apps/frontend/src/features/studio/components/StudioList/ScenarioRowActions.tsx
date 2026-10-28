import React from "react";
import { IconPlayerPlay } from "@tabler/icons-react";
import { ButtonLink } from "@/shared/components/ui/ButtonLink";
import { isLiveStatus } from "../../utils/scenarioRowStatus";
import { PlaytestButton } from "../PlaytestButton/PlaytestButton";
import { ScenarioRowMenu } from "./ScenarioRowMenu";
import type { ScenarioRowActionsProps } from "./StudioList.types";

const getEditLabel = (isDraft: boolean, isGuideDraft: boolean): string => {
  if (isGuideDraft) return "Continue";
  return isDraft ? "Continue editing" : "Edit";
};

export const ScenarioRowActions: React.FC<ScenarioRowActionsProps> = ({
  scenario,
  status,
  onDelete,
}) => {
  const editPath = `/studio/${scenario.scenario_id}/edit`;
  const isPublishing = status === "publishing";
  const isDraft = status === "draft";
  const isGuideDraft = isDraft && scenario.mode === "newbie";
  return (
    <div className="flex shrink-0 items-start gap-2">
      {isLiveStatus(status) && <PlaytestButton scenarioId={scenario.scenario_id} />}
      {!isPublishing && (
        <ButtonLink to={editPath} className="flex-1 sm:flex-none">
          {isDraft && <IconPlayerPlay size={16} aria-hidden="true" />}
          {getEditLabel(isDraft, isGuideDraft)}
        </ButtonLink>
      )}
      <ScenarioRowMenu scenario={scenario} status={status} onDelete={onDelete} />
    </div>
  );
};

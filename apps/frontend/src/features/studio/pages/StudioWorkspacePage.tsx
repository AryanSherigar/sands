import React, { useCallback, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { IconAlertCircle } from "@tabler/icons-react";
import { StudioFrame } from "../components/StudioFrame/StudioFrame";
import {
  FULL_EDITOR_PARAM,
  FULL_EDITOR_VALUE,
  LEGACY_MASTER_MODE_PARAM,
} from "../constants/studioFrame";
import { useStudioScenario } from "../hooks/useStudioScenario";
import { EditScenarioPage } from "./EditScenarioPage";
import { NewScenarioPage } from "./NewScenarioPage";
import { StrategyWorkspacePage } from "./StrategyWorkspacePage";

const CENTERED_CLASSES =
  "flex min-h-[100dvh] items-center justify-center gap-2 bg-surface-sunken font-sans text-sm";

export const StudioWorkspacePage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [draftId, setDraftId] = useState<string | null>(null);
  const scenarioId = id ?? draftId;
  const { scenario, isLoading, error } = useStudioScenario(scenarioId);

  const handleDraftCreated = useCallback(
    (createdId: string): void => {
      setDraftId(createdId);
      navigate(`/studio/${createdId}/edit`, { replace: true });
    },
    [navigate],
  );

  if (!scenarioId && searchParams.get("mode") === LEGACY_MASTER_MODE_PARAM) {
    return <NewScenarioPage />;
  }
  if (scenarioId && isLoading) {
    return <div className={`${CENTERED_CLASSES} text-content-muted`}>Loading story…</div>;
  }
  if (scenarioId && (error || !scenario)) {
    return (
      <div className={`${CENTERED_CLASSES} text-danger`}>
        <IconAlertCircle size={18} stroke={1.5} aria-hidden="true" />
        Couldn't load this story.
      </div>
    );
  }
  if (scenario?.mode === "strategy") return <StrategyWorkspacePage scenario={scenario} />;
  const isFullEditorRequested = searchParams.get(FULL_EDITOR_PARAM) === FULL_EDITOR_VALUE;
  if (scenario?.mode === "master" && isFullEditorRequested) return <EditScenarioPage />;

  return <StudioFrame scenarioId={scenarioId} onDraftCreated={handleDraftCreated} />;
};

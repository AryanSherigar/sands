import React from "react";
import { useParams } from "react-router-dom";
import { ScenarioLoadingSkeleton } from "../components/ScenarioFocus/ScenarioLoadingSkeleton";
import { ScenarioNotFound } from "../components/ScenarioFocus/ScenarioNotFound";
import { ScenarioPageContent } from "../components/ScenarioFocus/ScenarioPageContent/ScenarioPageContent";
import { useScenarioFocus } from "../hooks/useScenarioFocus";

export const ScenarioFocusPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const focus = useScenarioFocus(id);

  if (focus.isLoading) return <ScenarioLoadingSkeleton />;
  if (focus.isError || !focus.scenario) return <ScenarioNotFound />;

  return <ScenarioPageContent scenario={focus.scenario} focus={focus} />;
};

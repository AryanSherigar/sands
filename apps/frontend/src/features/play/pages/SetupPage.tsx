import React, { useState, useRef, useEffect } from "react";
import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "@/features/auth/hooks/useAuth";
import { useRequireAuth } from "@/shared/hooks/useRequireAuth";
import { getGenreAccentClass } from "@/shared/constants/genreAccent.constants";
import { Button } from "@/shared/components/ui/Button";
import { Toast } from "@/shared/components/feedback/Toast";
import { extractErrorMessage } from "@/shared/lib/extractErrorMessage";
import { getPrimaryGenre } from "../utils/scenarioPage.utils";
import { useScenarioFocus } from "../hooks/useScenarioFocus";
import { useCreatePlaythrough } from "../hooks/useSetup";
import { useCreatePlaytest } from "../hooks/useCreatePlaytest";
import {
  PLAYTEST_SEARCH_PARAM,
  PLAYTEST_SEARCH_VALUE,
} from "@/shared/constants/navigation";
import { SetupStageCard } from "../components/SetupScreen/SetupStageCard";
import { DramaticSetupLoader } from "../components/SetupScreen/DramaticSetupLoader";
import { StrategyRulerSetupScreen } from "../components/StrategyRulerSetup/StrategyRulerSetupScreen";

import { WelcomeTapeOverlay } from "../components/SetupScreen/WelcomeTapeOverlay";
import { hasWelcomeTape, getWelcomeHandoff, saveWelcomeHandoff, clearWelcomeHandoff } from "../utils/welcomeHandoff";

const SUBMIT_FAILED_DEFAULT_MESSAGE =
  "Failed to initialize campaign. Please check your setup choices and try again.";

export const SetupPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { isLoading: isAuthLoading } = useAuth();
  const requireAuth = useRequireAuth("setup");
  const {
    scenario,
    isLoading: isScenarioLoading,
    isError: isScenarioError,
  } = useScenarioFocus(id);
  const [searchParams] = useSearchParams();
  const isPlaytest =
    searchParams.get(PLAYTEST_SEARCH_PARAM) === PLAYTEST_SEARCH_VALUE;
  const createPlaythroughMutation = useCreatePlaythrough();
  const createPlaytestMutation = useCreatePlaytest();
  const startRunMutation = isPlaytest
    ? createPlaytestMutation
    : createPlaythroughMutation;

  const [isLoadingOverlay, setIsLoadingOverlay] = useState(false);
  const [createdPlaythroughId, setCreatedPlaythroughId] = useState<
    string | null
  >(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const [characterName, setCharacterName] = useState("");
  const isWelcomeTape = hasWelcomeTape(scenario?.world_data);
  useEffect(() => {
    const target = id && getWelcomeHandoff(id);
    if (target) {
      playthroughIdRef.current = target;
      navigate(`/play/${target}`, { replace: true });
    }
    return () => { if (id && playthroughIdRef.current) clearWelcomeHandoff(id); };
  }, [id, navigate]);

  const playthroughIdRef = useRef<string | null>(null);
  const loaderFinishedRef = useRef<boolean>(false);

  const handleSubmit = async (
    _formattedPayload: string,
    formValues: Record<string, unknown>,
  ) => {
    if (!scenario || !(await requireAuth())) return;

    setCharacterName(String(formValues.character_name ?? ""));
    setErrorMessage(null);
    playthroughIdRef.current = null;
    setCreatedPlaythroughId(null);
    loaderFinishedRef.current = false;
    setIsLoadingOverlay(true);

    try {
      const targetScenarioId = scenario.scenario_id || id || "";
      const result = await startRunMutation.mutateAsync({
        scenario_id: targetScenarioId,
        setup_values: formValues,
      });

      if (isWelcomeTape && id) saveWelcomeHandoff(id, result.playthrough_id);
      playthroughIdRef.current = result.playthrough_id;
      setCreatedPlaythroughId(result.playthrough_id);

      if (loaderFinishedRef.current) {
        navigate(`/play/${result.playthrough_id}`);
      }
    } catch (err: unknown) {
      setIsLoadingOverlay(false);
      setCreatedPlaythroughId(null);
      setErrorMessage(
        extractErrorMessage(err, SUBMIT_FAILED_DEFAULT_MESSAGE),
      );
    }
  };

  const handleLoaderComplete = () => {
    setIsLoadingOverlay(false);
    loaderFinishedRef.current = true;
    const targetId = createdPlaythroughId || playthroughIdRef.current;
    if (targetId) {
      navigate(`/play/${targetId}`);
    }
  };

  if (isAuthLoading || isScenarioLoading) {
    return (
      <div className="min-h-dvh w-full bg-surface-sunken flex flex-col items-center justify-center space-y-4">
        <div className="w-8 h-8 border-2 border-border-strong border-t-primary rounded-full animate-spin" />
        <p className="font-mono text-xs text-content-muted tracking-widest uppercase">
          CALIBRATING SCENARIO REALM...
        </p>
      </div>
    );
  }

  if (isScenarioError || !scenario) {
    return (
      <div className="min-h-dvh w-full bg-surface-sunken text-content flex flex-col items-center justify-center p-6 text-center space-y-6">
        <div className="z-10 space-y-4 max-w-[640px] mx-auto">
          <h1 className="font-display text-2xl font-bold text-danger">
            Scenario Not Found
          </h1>
          <p className="font-sans text-sm text-content-muted max-w-md mx-auto">
            The requested scenario could not be loaded or is unavailable.
          </p>
          <Button
            variant="secondary"
            size="md"
            onClick={() => navigate("/discover")}
          >
            Return to Discover
          </Button>
        </div>
      </div>
    );
  }

  if (scenario.mode === "strategy") {
    return (
      <StrategyRulerSetupScreen
        scenario={scenario}
        isPlaytest={isPlaytest}
      />
    );
  }

  const primaryGenre = getPrimaryGenre(scenario.genre_tags);
  const genreAccentClass = getGenreAccentClass(primaryGenre);

  return (
    <div
      className={`${genreAccentClass} relative min-h-dvh w-full bg-surface-sunken text-content flex items-center justify-center p-4 sm:p-6 md:p-10 overflow-x-hidden font-sans`}
    >

      <div className="absolute inset-0 bg-radial from-transparent via-surface-sunken/70 to-surface-sunken pointer-events-none" />

      <div className="w-full max-w-[640px] mx-auto relative z-10">
        <SetupStageCard
          scenario={scenario}
          onSubmit={handleSubmit}
          isSubmitting={startRunMutation.isPending || isLoadingOverlay}
        />
      </div>

      {isLoadingOverlay && isWelcomeTape && <WelcomeTapeOverlay playthroughId={createdPlaythroughId} characterName={characterName} onComplete={handleLoaderComplete} />}
      {isLoadingOverlay && !isWelcomeTape && (
        <DramaticSetupLoader
          scenarioTitle={scenario.title}
          isReady={Boolean(createdPlaythroughId)}
          onComplete={handleLoaderComplete}
        />
      )}

      {errorMessage && (
        <Toast
          message={errorMessage}
          type="error"
          onClose={() => setErrorMessage(null)}
        />
      )}
    </div>
  );
};

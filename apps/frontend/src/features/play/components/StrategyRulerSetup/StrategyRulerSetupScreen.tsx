import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useRequireAuth } from "@/shared/hooks/useRequireAuth";
import { useCreatePlaythrough } from "@/features/play/hooks/useSetup";
import { useCreatePlaytest } from "@/features/play/hooks/useCreatePlaytest";
import { useStrategyMap } from "@/features/play/hooks/useStrategyMap";
import { Toast } from "@/shared/components/feedback/Toast";
import { extractErrorMessage } from "@/shared/lib/extractErrorMessage";
import { useStrategySetupState } from "./useStrategySetupState";
import { StrategyRealmExplorer } from "./StrategyRealmExplorer";
import { StrategyRulerPersona } from "./StrategyRulerPersona";
import { StrategyCampaignLoader } from "./StrategyCampaignLoader";
import type { ScenarioDetailResponse } from "@/features/play/types/scenario";

export interface StrategyRulerSetupScreenProps {
  scenario: (ScenarioDetailResponse | Partial<ScenarioDetailResponse>) & { id?: string };
  isPlaytest?: boolean;
}

export const StrategyRulerSetupScreen: React.FC<StrategyRulerSetupScreenProps> = ({
  scenario,
  isPlaytest = false,
}) => {
  const navigate = useNavigate();
  const requireAuth = useRequireAuth("setup");
  const createPlaythroughMutation = useCreatePlaythrough();
  const createPlaytestMutation = useCreatePlaytest();
  const startRunMutation = isPlaytest
    ? createPlaytestMutation
    : createPlaythroughMutation;
  const targetScenarioId =
    scenario?.scenario_id ||
    (scenario && "id" in scenario && typeof scenario.id === "string"
      ? scenario.id
      : "");

  const { data: mapDoc } = useStrategyMap(targetScenarioId);

  const {
    activeFactionId,
    setActiveFactionId,
    ruler,
    updateRuler,
    isRedrafting,
    redraftBackstory,
    restoreDefaultRuler,
    validation,
    isValid,
    factions,
    availableTraits,
    availableAmbitions,
  } = useStrategySetupState(scenario);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleBeginReign = async () => {
    if (!isPlaytest && !(await requireAuth())) return;

    if (!isValid) {
      const firstError =
        validation.name ||
        validation.traits ||
        validation.ambitions ||
        validation.faction ||
        "Please resolve setup errors before proceeding.";
      setErrorMessage(firstError);
      return;
    }

    setErrorMessage(null);
    setIsSubmitting(true);

    try {
      if (import.meta.env.DEV && targetScenarioId === "strategy-preview") {
        await new Promise((resolve) => setTimeout(resolve, 4500));
        navigate("/play/strategy-preview");
        return;
      }

      const result = await startRunMutation.mutateAsync({
        scenario_id: targetScenarioId,
        faction_id: activeFactionId,
        player_ruler: {
          name: ruler.name,
          epithet: ruler.epithet || null,
          portrait_url: ruler.portraitUrl || null,
          trait_ids: ruler.traitIds,
          ambition_ids: ruler.ambitionIds,
          backstory: ruler.backstory,
        },
      });

      navigate(`/play/${result.playthrough_id}`);
    } catch (err: unknown) {
      setIsSubmitting(false);
      setErrorMessage(
        extractErrorMessage(
          err,
          "Failed to begin reign. Please check your setup choices and try again.",
        ),
      );
    }
  };

  return (
    <div className="relative min-h-screen w-full bg-[#EFE4C8] text-[#3A3128] font-['Manrope',sans-serif] p-4 sm:p-6 lg:p-8 overflow-x-hidden">
      {/* Ambient Mist and Watercolor Glow */}
      <div className="pointer-events-none fixed -top-40 -left-40 w-96 h-96 bg-[#DCE7EA]/60 rounded-full blur-3xl" />
      <div className="pointer-events-none fixed top-1/3 -right-40 w-96 h-96 bg-[#D2A94A]/20 rounded-full blur-3xl" />
      <div className="pointer-events-none fixed -bottom-40 left-1/3 w-96 h-96 bg-[#5E8A5A]/15 rounded-full blur-3xl" />

      <div className="relative z-10 max-w-7xl mx-auto">
        {/* Header */}
        <header className="mb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#3A3128]/15 pb-6">
          <div>
            <div className="flex items-center gap-2 text-xs font-semibold tracking-wider uppercase text-[#72787C] font-['Manrope',sans-serif] mb-1">
              <span className="w-1.5 h-1.5 rounded-full bg-[#D2A94A]" />
              <span>Parchment Chronicle • Section VIII</span>
            </div>
            <h1 className="text-3xl sm:text-4xl font-bold text-[#3A3128] font-['EB_Garamond',serif] tracking-tight">
              Ruler Setup &amp; Backstory
            </h1>
            <p className="text-sm text-[#72787C] font-serif italic mt-0.5">
              Inscribe the annals of your reign before coronation heralds ride forth.
            </p>
          </div>
          <div className="flex items-center gap-2.5 self-start sm:self-auto px-3.5 py-1.5 rounded-full bg-[#F3EAD3] border border-[#3A3128]/20 shadow-sm">
            <span className="w-2 h-2 rounded-full bg-[#5E8A5A] animate-pulse" />
            <span className="text-xs font-semibold tracking-wide text-[#3A3128] font-['Manrope',sans-serif]">
              Anno Domini 1042 / Campaign Turn 0
            </span>
          </div>
        </header>

        {/* Workspace: 2-column layout */}
        <main className="grid grid-cols-1 xl:grid-cols-12 gap-6 xl:gap-8">
          <div className="xl:col-span-6">
            <StrategyRealmExplorer
              factions={factions}
              activeFactionId={activeFactionId}
              onSelectFaction={setActiveFactionId}
              mapDoc={mapDoc}
            />
          </div>
          <div className="xl:col-span-6">
            <StrategyRulerPersona
              ruler={ruler}
              onUpdateRuler={updateRuler}
              onRedraftBackstory={redraftBackstory}
              isRedrafting={isRedrafting}
              availableTraits={availableTraits}
              availableAmbitions={availableAmbitions}
              onResetDefault={restoreDefaultRuler}
              onBeginReign={handleBeginReign}
              isSubmitting={isSubmitting}
            />
          </div>
        </main>

        {/* Footer: Chronicle footnote ribbon */}
        <footer className="mt-12 pt-6 border-t border-[#3A3128]/15 text-center flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-[#72787C] font-['Manrope',sans-serif]">
          <div className="flex items-center gap-2 text-left">
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-[#D2A94A] shrink-0" />
            <span>
              Living Historical Engine active • Treaties, sovereign memories, and provincial unrest will simulate upon coronation.
            </span>
          </div>
          <span className="font-serif italic text-[#3A3128]/70 shrink-0">
            Wilds Chronicle Edition • Turn 0
          </span>
        </footer>
      </div>

      {/* Transition Loader overlay */}
      {isSubmitting && <StrategyCampaignLoader />}

      {/* Error Toast */}
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

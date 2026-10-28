import React, { useEffect, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { useAuthStore } from "@/features/auth/stores/auth.store";
import { buildStepVariants } from "@/shared/lib/motion-variants";
import {
  ONBOARDING_REDIRECT_PARAM,
  ONBOARDING_REDO_PARAM,
  SETTINGS_PATH,
  buildDiscoverHref,
  sanitizeRedirectTarget,
} from "@/shared/lib/onboarding-routes";
import { DoneStep } from "../components/DoneStep/DoneStep";
import { GenresStep } from "../components/GenresStep/GenresStep";
import { ProfileStep } from "../components/ProfileStep/ProfileStep";
import { ReadingStep } from "../components/ReadingStep/ReadingStep";
import { SetUpLaterDialog } from "../components/SetUpLaterDialog/SetUpLaterDialog";
import { WelcomeStep } from "../components/WelcomeStep/WelcomeStep";
import { WizardTopBar } from "../components/WizardTopBar/WizardTopBar";
import { WizardProgress } from "../components/WizardProgress/WizardProgress";
import { ONBOARDING_ERROR_MESSAGE } from "../constants/onboarding.constants";
import { useCompleteOnboarding } from "../hooks/useCompleteOnboarding";
import { useRedoPrefill } from "../hooks/useRedoPrefill";
import { useOnboardingStore } from "../stores/onboarding.store";

export const WelcomePage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const redirectTarget = sanitizeRedirectTarget(
    searchParams.get(ONBOARDING_REDIRECT_PARAM),
  );
  const isRedo = searchParams.get(ONBOARDING_REDO_PARAM) === "1";
  const user = useAuthStore((state) => state.user);
  const [wasAlreadyCompleted] = useState(user?.onboarding_completed === true);
  const [isSetUpLaterOpen, setIsSetUpLaterOpen] = useState(false);
  const step = useOnboardingStore((state) => state.step);
  const goToStep = useOnboardingStore((state) => state.goToStep);
  const genres = useOnboardingStore((state) => state.genres);
  const resetWizard = useOnboardingStore((state) => state.reset);
  const completion = useCompleteOnboarding(isRedo);
  const shouldReduceMotion = useReducedMotion() ?? false;

  useEffect(() => {
    resetWizard(useAuthStore.getState().user?.display_name ?? "");
    return () => resetWizard("");
  }, [resetWizard]);
  useRedoPrefill(isRedo);

  if (wasAlreadyCompleted && !isRedo) {
    return <Navigate to={redirectTarget ?? "/"} replace />;
  }

  const handleFinish = () =>
    completion.mutate(undefined, { onSuccess: () => goToStep("done") });
  const handleConfirmSetUpLater = () =>
    isRedo
      ? navigate(SETTINGS_PATH, { replace: true })
      : completion.mutate(undefined, {
          onSuccess: () => navigate(redirectTarget ?? "/", { replace: true }),
        });
  const handleCancelSetUpLater = () => {
    completion.reset();
    setIsSetUpLaterOpen(false);
  };
  const errorMessage = completion.isError ? ONBOARDING_ERROR_MESSAGE : null;

  const isProgressVisible =
    step === "genres" || step === "profile" || step === "reading";

  return (
    <main className="relative flex min-h-dvh flex-col justify-between overflow-x-hidden bg-surface font-sans text-content selection:bg-surface-overlay selection:text-content">
      {/* Ambient subtle mist gradient at top */}
      <div
        className="pointer-events-none fixed inset-x-0 top-0 z-0 h-64 bg-linear-to-b from-white/2 to-transparent"
        aria-hidden="true"
      />

      <div className="relative z-10 mx-auto flex w-full max-w-[640px] flex-1 flex-col px-6 pb-12">
        {step !== "done" && (
          <WizardTopBar onSetUpLater={() => setIsSetUpLaterOpen(true)} />
        )}
        <div className="flex flex-1 flex-col justify-center py-6">
          {isProgressVisible && <WizardProgress currentStep={step} />}
          <AnimatePresence mode="wait">
            <motion.div
              key={step}
              variants={buildStepVariants(shouldReduceMotion)}
              initial="initial"
              animate="animate"
              exit="exit"
            >
              {step === "welcome" && (
                <WelcomeStep onStart={() => goToStep("genres")} />
              )}
              {step === "genres" && (
                <GenresStep
                  onBack={() => goToStep("welcome")}
                  onSkip={() => goToStep("profile")}
                  onNext={() => goToStep("profile")}
                />
              )}
              {step === "profile" && (
                <ProfileStep
                  onBack={() => goToStep("genres")}
                  onSkip={() => goToStep("reading")}
                  onNext={() => goToStep("reading")}
                />
              )}
              {step === "reading" && (
                <ReadingStep
                  onBack={() => goToStep("profile")}
                  onSkip={handleFinish}
                  onFinish={handleFinish}
                  isSaving={completion.isPending}
                  errorMessage={errorMessage}
                />
              )}
              {step === "done" && (
                <DoneStep
                  genres={genres}
                  exploreHref={isRedo ? SETTINGS_PATH : (redirectTarget ?? buildDiscoverHref(genres))}
                />
              )}
            </motion.div>
          </AnimatePresence>
        </div>
      </div>

      <SetUpLaterDialog
        isOpen={isSetUpLaterOpen}
        isSaving={completion.isPending}
        errorMessage={errorMessage}
        onConfirm={handleConfirmSetUpLater}
        onCancel={handleCancelSetUpLater}
      />
    </main>
  );
};

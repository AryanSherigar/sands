import type { ComponentType } from "react";
import type { GuideStepId } from "../../constants/guideSteps";
import { StepCharacters } from "./StepCharacters";
import { StepEndings } from "./StepEndings";
import { StepExtras } from "./StepExtras";
import { StepFinish } from "./StepFinish";
import { StepHardLimits } from "./StepHardLimits";
import { StepIdea } from "./StepIdea";
import { StepOpening } from "./StepOpening";
import { StepPlayer } from "./StepPlayer";
import { StepPremise } from "./StepPremise";
import { StepRules } from "./StepRules";
import { StepTrackedValues } from "./StepTrackedValues";
import { StepWorld } from "./StepWorld";

export const GUIDE_STEP_COMPONENTS: Record<GuideStepId, ComponentType> = {
  idea: StepIdea,
  premise: StepPremise,
  player: StepPlayer,
  characters: StepCharacters,
  world: StepWorld,
  opening: StepOpening,
  endings: StepEndings,
  tracked_values: StepTrackedValues,
  rules: StepRules,
  hard_limits: StepHardLimits,
  extras: StepExtras,
  finish: StepFinish,
};

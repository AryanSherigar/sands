import { useContext } from "react";
import { GuideContext } from "../components/Guide/guideContext";
import { ADVANCED_MODE_ON } from "../constants/advancedMode";

export const useIsAdvancedMode = (): boolean => {
  const guide = useContext(GuideContext);
  return guide?.scenario?.mode === ADVANCED_MODE_ON;
};

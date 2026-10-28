import { useContext } from "react";
import { GuideContext, type GuideContextValue } from "../components/Guide/guideContext";

export const useGuide = (): GuideContextValue => {
  const value = useContext(GuideContext);
  if (!value) throw new Error("useGuide must be used inside GuideScenarioProvider.");
  return value;
};

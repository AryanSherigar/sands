import { AlphaIntakeGate } from "@/shared/components/alpha-survey/AlphaIntakeGate/AlphaIntakeGate";
import { useAlphaCollection } from "@/shared/hooks/useAlphaCollection";
import { useAlphaSession } from "@/shared/hooks/useAlphaSession";

export function AlphaCollectionBridge() {
  const isCollecting = useAlphaCollection();
  useAlphaSession(isCollecting);
  return isCollecting ? <AlphaIntakeGate /> : null;
}

import { AnimatedPortrait } from "@/shared/components/AnimatedPortrait/AnimatedPortrait";
import type { RulerMeshAvatarProps } from "./RulerMeshAvatar.types";

export function RulerMeshAvatar({ leaderName, factionName, fallbackCrest, ...props }: RulerMeshAvatarProps) {
  return <AnimatedPortrait {...props} fallbackSrc={fallbackCrest} label={`${leaderName} of ${factionName}`} />;
}

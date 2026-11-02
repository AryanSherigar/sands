/**
 * RulerMeshAvatar types
 *
 * Types for WebGL2 2D mesh avatar component.
 * Upstream attribution: shinshin86/mesh-avatar-studio (https://github.com/shinshin86/mesh-avatar-studio)
 * Copyright (c) 2026 Yuki Shindo
 * Licensed under the MIT License.
 */

import type { AnimatedPortraitProps } from "@/shared/components/AnimatedPortrait/AnimatedPortrait.types";
export type { AvatarExpression } from "@/shared/components/AnimatedPortrait/AnimatedPortrait.types";

export interface RulerMeshAvatarProps extends Omit<AnimatedPortraitProps, "fallbackSrc" | "label"> {
  fallbackCrest: string;
  leaderName: string;
  factionName: string;
}

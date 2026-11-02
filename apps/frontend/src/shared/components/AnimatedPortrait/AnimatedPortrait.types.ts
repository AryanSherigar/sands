/**
 * RulerMeshAvatar types
 *
 * Types for WebGL2 2D mesh avatar component.
 * Upstream attribution: shinshin86/mesh-avatar-studio (https://github.com/shinshin86/mesh-avatar-studio)
 * Copyright (c) 2026 Yuki Shindo
 * Licensed under the MIT License.
 */

export type AvatarExpression =
  | "neutral"
  | "smile"
  | "shy"
  | "surprise"
  | "halfLidded"
  | "angry"
  | "sad"
  | "wink";

export interface AnimatedPortraitProps {
  avatarUrl?: string | null;
  portraitUrl?: string | null;
  fallbackSrc: string;
  label: string;
  expression?: AvatarExpression;
  isSpeaking?: boolean;
  className?: string;
  onLoad?: () => void;
  onError?: (error: Error) => void;
}

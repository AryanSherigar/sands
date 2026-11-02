/**
 * RulerMeshAvatar component
 *
 * Integrates 2D mesh avatar animations using mesh-avatar-react with graceful 2D fallbacks.
 *
 * Upstream attribution: shinshin86/mesh-avatar-studio (https://github.com/shinshin86/mesh-avatar-studio)
 * Copyright (c) 2026 Yuki Shindo
 * Licensed under the MIT License.
 */

import React, { useEffect, useRef, useState } from "react";
import { MeshAvatar, type MeshAvatarElement } from "mesh-avatar-react";
import { useIsMotionReduced } from "@/shared/hooks/useIsMotionReduced";
import type { AnimatedPortraitProps } from "./AnimatedPortrait.types";

function isWebGL2Available(): boolean {
  return typeof window !== "undefined" && Boolean(window.WebGL2RenderingContext);
}

export const AnimatedPortrait: React.FC<AnimatedPortraitProps> = ({
  avatarUrl,
  portraitUrl,
  fallbackSrc,
  label,
  expression = "neutral",
  isSpeaking = false,
  className = "w-full h-full object-cover object-top",
  onLoad,
  onError,
}) => {
  const [hasError, setHasError] = useState(false);
  const [hasStillError, setStillError] = useState(false);
  const isMotionReduced = useIsMotionReduced();
  const avatarRef = useRef<MeshAvatarElement>(null);
  const supportsWebGL2 = useRef<boolean | null>(null);

  if (supportsWebGL2.current === null) {
    supportsWebGL2.current = isWebGL2Available();
  }

  useEffect(() => {
    setHasError(false);
    setStillError(false);
  }, [avatarUrl, portraitUrl]);

  useEffect(() => {
    const el = avatarRef.current;
    if (!el) return;
    try {
      el.avatar?.setSpeaking(isSpeaking);
      if (isSpeaking) {
        el.setVoiceLevel(0.65);
      } else {
        el.setVoiceLevel(0);
      }
    } catch {
      // Best-effort lip-sync update
    }
  }, [isSpeaking]);

  useEffect(() => {
    return () => {
      // The mesh may mount after this effect if the avatar URL changes.
      // eslint-disable-next-line react-hooks/exhaustive-deps
      const el = avatarRef.current;
      if (el?.avatar) {
        try {
          el.avatar.destroy();
        } catch {
          // Cleanup best effort
        }
      }
    };
  }, []);

  const handleLoad = () => {
    onLoad?.();
    const el = avatarRef.current;
    if (!el) return;
    try {
      el.avatar?.setSpeaking(isSpeaking);
      if (isSpeaking) {
        el.setVoiceLevel(0.65);
      } else {
        el.setVoiceLevel(0);
      }
    } catch {
      // Best-effort lip-sync update
    }
  };

  const shouldRenderMesh = Boolean(avatarUrl && !hasError && !isMotionReduced && supportsWebGL2.current);
  const generatedStill = avatarUrl?.replace(/(\/avatars\/[0-9a-f-]{36})\.mavatar$/i, "$1.png");
  const imageSrc = hasStillError ? fallbackSrc : (portraitUrl || (generatedStill !== avatarUrl ? generatedStill : null) || fallbackSrc);

  if (!shouldRenderMesh) {
    return (
      <img
        src={imageSrc}
        alt={label}
        onError={() => { if (imageSrc !== fallbackSrc) setStillError(true); }}
        className={`${className} filter contrast-[1.02] brightness-[0.98] ${isMotionReduced ? "" : "transition-transform duration-700 ease-out group-hover:scale-105"}`}
      />
    );
  }

  return (
    <div className="relative w-full h-full flex items-center justify-center overflow-hidden">
      <MeshAvatar
        ref={avatarRef}
        src={avatarUrl!}
        expression={expression}
        label={label}
        onLoad={handleLoad}
        onError={(error) => { setHasError(true); onError?.(error instanceof Error ? error : new Error(String(error))); }}
        style={{ width: "100%", height: "100%", display: "block" }}
      />
    </div>
  );
};

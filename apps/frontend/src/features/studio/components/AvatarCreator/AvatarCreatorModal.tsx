import React, { useState } from "react";
import { Button } from "@/shared/components/ui/Button";
import { AnimatedPortrait } from "@/shared/components/AnimatedPortrait/AnimatedPortrait";
import type { AvatarExpression } from "@/shared/components/AnimatedPortrait/AnimatedPortrait.types";
import { optimizeAvatarPrompt, buildMeshAvatar, generateLeaderPortrait } from "../../api/avatarStudio.api";
import { fetchPortraitBlob, readPortraitAsDataUrl } from "./portraitImage";
import { PremadeAvatarPicker } from "./PremadeAvatarPicker";
import type { PremadeAvatar } from "../../types/premade_avatar.types";
import { logEvent } from "@/shared/lib/logger";

// NOTE: mirrors FRAMING_DIRECTIVE in core-api avatar_prompt_service.py; used only when the optimize call fails.
const AVATAR_FRAMING_DIRECTIVE =
  "face centered and symmetrical, eyes level about 42% of the way down the frame, head top near the upper edge, chin about three quarters of the way down, shoulders cropped by the bottom edge, hair kept clear of the eyes";
const BUILD_AVATAR_FALLBACK_MESSAGE = "Could not build the avatar. Check your portrait and try again.";

interface AvatarCreatorModalProps {
  isOpen: boolean;
  onClose: () => void;
  characterName: string;
  characterLabel: string;
  dialogLabel?: string;
  attachLabel?: string;
  currentAvatarUrl?: string | null;
  currentPortraitUrl?: string | null;
  onSavePortrait?: (portraitUrl: string) => void;
  onSave: (avatarUrl: string) => void | Promise<void>;
}

export const AvatarCreatorModal: React.FC<AvatarCreatorModalProps> = ({
  isOpen,
  onClose,
  characterName,
  characterLabel,
  dialogLabel = "Create animated character avatar",
  attachLabel = "Attach to character",
  currentAvatarUrl,
  currentPortraitUrl,
  onSavePortrait,
  onSave,
}) => {
  const [description, setDescription] = useState("");
  const [optimizedPrompt, setOptimizedPrompt] = useState("");
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [hasPreviewError, setPreviewError] = useState(false);
  const [isPreviewVerified, setPreviewVerified] = useState(Boolean(currentAvatarUrl));
  const [portrait, setPortrait] = useState<File | null>(null);
  const [portraitUrl, setPortraitUrl] = useState<string | null>(currentPortraitUrl ?? null);
  const [isPortraitGenerating, setPortraitGenerating] = useState(false);
  const [previewAvatarUrl, setPreviewAvatarUrl] = useState<string | null>(
    currentAvatarUrl ?? null,
  );
  const [testExpression, setTestExpression] = useState<AvatarExpression>("neutral");
  const [isSpeakingTest, setIsSpeakingTest] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleOptimizePrompt = async () => {
    if (!description.trim()) return;
    setIsOptimizing(true);
    setErrorMessage(null);
    try {
      const prompt = await optimizeAvatarPrompt(description);
      setOptimizedPrompt(prompt);
    } catch {
      // Fallback local optimization
      setOptimizedPrompt(
        `Front-facing bust portrait of ${description}, head and shoulders, ${AVATAR_FRAMING_DIRECTIVE}, resting closed mouth, clean eye contours, crisp lighting, isolated neutral background.`
      );
    } finally {
      setIsOptimizing(false);
    }
  };

  const handleGeneratePortrait = async () => {
    setPortraitGenerating(true);
    setErrorMessage(null);
    try {
      setPortraitUrl(await generateLeaderPortrait(optimizedPrompt));
      setPortrait(null);
    } catch {
      setErrorMessage("We could not generate a portrait. Try again.");
    } finally {
      setPortraitGenerating(false);
    }
  };

  const handleGenerateMesh = async () => {
    if (!portrait && !portraitUrl) return;
    setIsGenerating(true);
    setErrorMessage(null);
    try {
      const image = portrait ?? await fetchPortraitBlob(portraitUrl!);
      const imageUrl = await readPortraitAsDataUrl(image);
      const res = await buildMeshAvatar(characterName, imageUrl);
      setPreviewError(false);
      setPreviewVerified(false);
      setPreviewAvatarUrl(res.avatar_url);
    } catch (error) {
      logEvent("warning", "avatar_build_failed", { error: String(error), has_upload: Boolean(portrait) });
      setErrorMessage(BUILD_AVATAR_FALLBACK_MESSAGE);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleSelectPremade = (avatar: PremadeAvatar) => {
    setErrorMessage(null);
    setPreviewError(false);
    setPreviewVerified(false);
    setPreviewAvatarUrl(avatar.avatar_url);
  };

  const handleSave = async () => {
    if (!previewAvatarUrl) return;
    setIsSaving(true);
    setErrorMessage(null);
    try {
      await onSave(previewAvatarUrl);
      onClose();
    } catch {
      setErrorMessage("Could not attach the avatar. Please try again.");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 select-none"
      role="dialog"
      aria-modal="true"
      aria-label={dialogLabel}
    >
      <div className="w-full max-w-2xl bg-surface-raised border border-border-strong rounded-xl shadow-2xl p-6 space-y-5 flex flex-col max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between border-b border-border-subtle pb-3">
          <div>
            <h2 className="text-lg font-bold text-text-primary">
              Animated Avatar Studio
            </h2>
            <p className="text-xs text-text-muted">
              Create an animated 2D mesh avatar for {characterLabel}
            </p>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose} aria-label="Close">
            ✕
          </Button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-4">
            <PremadeAvatarPicker selectedAvatarUrl={previewAvatarUrl} onSelect={handleSelectPremade} />
            <div>
              <label className="block text-xs font-semibold text-text-secondary mb-1">
                Character Concept Description
              </label>
              <textarea
                className="w-full h-24 p-2.5 text-sm bg-surface-inset border border-border-subtle rounded-md focus:border-accent focus:outline-none resize-none"
                placeholder="e.g. Stern elven queen in silver battle armor, icy blue eyes, silver crown..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
              <Button
                type="button"
                variant="secondary"
                size="sm"
                className="mt-2 w-full"
                disabled={isOptimizing || !description.trim()}
                onClick={handleOptimizePrompt}
              >
                {isOptimizing ? "Preparing..." : "Prepare portrait prompt"}
              </Button>
            </div>

            {optimizedPrompt && (
              <div className="space-y-2">
                <label className="block text-xs font-semibold text-text-secondary">
                  Rig-Optimized Prompt (Front-facing, closed mouth)
                </label>
                <div className="p-2.5 bg-surface-overlay text-xs text-text-secondary rounded border border-border-subtle italic">
                  {optimizedPrompt}
                </div>
                <Button type="button" variant="secondary" size="sm" className="w-full" disabled={isPortraitGenerating} onClick={handleGeneratePortrait}>{isPortraitGenerating ? "Generating..." : `${portraitUrl ? "Regenerate" : "Generate"} Portrait`}</Button>
              </div>
            )}

            {portraitUrl && <div className="space-y-2"><img src={portraitUrl} alt="Portrait preview" className="w-full max-h-56 object-contain rounded border border-border-subtle" />{onSavePortrait && <Button type="button" variant="secondary" size="sm" onClick={() => onSavePortrait(portraitUrl)}>Use this portrait</Button>}</div>}

            <label className="block text-xs font-semibold text-text-secondary">
              Choose portrait (PNG, JPEG or WebP; up to 5 MB)
              <input type="file" accept="image/png,image/jpeg,image/webp" className="mt-2 block w-full text-sm" onChange={(event) => {
                const file = event.target.files?.[0] ?? null;
                setPortrait(file && file.size <= 5 * 1024 * 1024 ? file : null);
                if (file) setPortraitUrl(null);
                setErrorMessage(file && file.size > 5 * 1024 * 1024 ? "Choose an image smaller than 5 MB." : null);
              }} />
            </label>
            <p className="text-xs text-text-muted">Eye and mouth positions are approximate. Use a centered, front-facing portrait and check the animated preview before attaching.</p>
            <Button type="button" variant="primary" size="sm" className="w-full" disabled={isGenerating || (!portrait && !portraitUrl)} onClick={handleGenerateMesh}>
              {isGenerating ? "Building avatar..." : "Build avatar"}
            </Button>

            {errorMessage && (
              <p role="alert" className="text-xs text-error font-medium">{errorMessage}</p>
            )}
            {previewAvatarUrl && !isPreviewVerified && !hasPreviewError && !isGenerating && (
              <p role="status" className="text-xs text-text-muted">Waiting for the animated preview. Browser graphics and motion must be enabled to verify it before attaching.</p>
            )}
          </div>

          <div className="flex flex-col items-center justify-center p-4 bg-surface-inset rounded-lg border border-border-subtle space-y-3">
            <span className="text-xs font-semibold text-text-secondary uppercase tracking-wider">
              Live WebGL Preview
            </span>
            <div className="relative w-48 h-56 rounded-lg overflow-hidden border border-border-strong bg-black/20 shadow-inner flex items-center justify-center">
              {previewAvatarUrl ? (
                <AnimatedPortrait
                  avatarUrl={previewAvatarUrl}
                  fallbackSrc="data:image/svg+xml;utf8,<svg></svg>"
                  label={characterLabel}
                  expression={testExpression}
                  isSpeaking={isSpeakingTest}
                  onLoad={() => setPreviewVerified(true)}
                  onError={() => { setPreviewError(true); setErrorMessage("The avatar could not be displayed. Choose another portrait or try again."); }}
                />
              ) : (
                <span className="text-xs text-text-muted">No preview available</span>
              )}
            </div>

            <div className="space-y-1.5 w-full text-center">
              <span className="text-[11px] text-text-muted font-medium">
                Test Expression & Speech
              </span>
              <div className="flex flex-wrap items-center justify-center gap-1.5">
                {(["neutral", "smile", "angry", "halfLidded", "surprise"] as AvatarExpression[]).map(
                  (expr) => (
                    <button
                      key={expr}
                      type="button"
                      onClick={() => setTestExpression(expr)}
                      className={`px-2 py-0.5 text-[11px] rounded capitalize transition-colors ${
                        testExpression === expr
                          ? "bg-accent text-accent-contrast font-bold"
                          : "bg-surface-raised text-text-secondary hover:bg-surface-overlay"
                      }`}
                    >
                      {expr}
                    </button>
                  ),
                )}
                <button
                  type="button"
                  onClick={() => setIsSpeakingTest((prev) => !prev)}
                  className={`px-2 py-0.5 text-[11px] rounded transition-colors ${
                    isSpeakingTest
                      ? "bg-warning text-warning-contrast font-bold"
                      : "bg-surface-raised text-text-secondary hover:bg-surface-overlay"
                  }`}
                >
                  {isSpeakingTest ? "Speaking ●" : "Test Voice"}
                </button>
              </div>
            </div>
          </div>
        </div>

        <div className="flex items-center justify-end gap-3 pt-3 border-t border-border-subtle">
          <Button variant="ghost" size="sm" onClick={onClose}>
            Cancel
          </Button>
          <Button
            variant="primary"
            size="sm"
            disabled={!previewAvatarUrl || !isPreviewVerified || hasPreviewError || isSaving || isGenerating}
            onClick={handleSave}
          >
            {isSaving ? "Saving..." : attachLabel}
          </Button>
        </div>
      </div>
    </div>
  );
};

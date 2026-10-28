import { useState } from "react";
import {
  DEFAULT_AVATAR,
  DEFAULT_BANNER,
} from "@/shared/constants/profile-presets";
import { uploadAvatar, uploadBanner } from "../api/profileApi";
import {
  AVATAR_UPLOAD_FAILED_MESSAGE,
  BANNER_UPLOAD_FAILED_MESSAGE,
  EMPTY_NAME_MESSAGE,
  SAVE_FAILED_MESSAGE,
} from "../constants/editProfile.constants";
import type { UserProfile } from "../types/profile.types";
import { useProfileImageUpload } from "./useProfileImageUpload";
import { useUpdateProfile } from "./useUpdateProfile";

export interface ProfileDraft {
  displayName: string;
  bio: string;
  avatarUrl: string;
  bannerUrl: string;
}

export const useEditProfileForm = (profile: UserProfile, onClose: () => void) => {
  const [draft, setDraft] = useState<ProfileDraft>({
    displayName: profile.display_name,
    bio: profile.bio || "",
    avatarUrl: profile.avatar_url || DEFAULT_AVATAR,
    bannerUrl: profile.banner_url || DEFAULT_BANNER,
  });
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const updateMutation = useUpdateProfile();

  const updateDraft = (changes: Partial<ProfileDraft>) =>
    setDraft((current) => ({ ...current, ...changes }));

  const avatarUpload = useProfileImageUpload({
    upload: uploadAvatar,
    onUploaded: (avatarUrl) => updateDraft({ avatarUrl }),
    onError: setErrorMessage,
    failureMessage: AVATAR_UPLOAD_FAILED_MESSAGE,
  });
  const bannerUpload = useProfileImageUpload({
    upload: uploadBanner,
    onUploaded: (bannerUrl) => updateDraft({ bannerUrl }),
    onError: setErrorMessage,
    failureMessage: BANNER_UPLOAD_FAILED_MESSAGE,
  });

  const handleSave = async (event: React.FormEvent) => {
    event.preventDefault();
    setErrorMessage(null);
    if (!draft.displayName.trim()) {
      setErrorMessage(EMPTY_NAME_MESSAGE);
      return;
    }
    try {
      await updateMutation.mutateAsync({
        display_name: draft.displayName.trim(),
        bio: draft.bio.trim() || null,
        avatar_url: draft.avatarUrl,
        banner_url: draft.bannerUrl,
      });
      onClose();
    } catch {
      setErrorMessage(SAVE_FAILED_MESSAGE);
    }
  };

  return {
    draft,
    updateDraft,
    errorMessage,
    avatarUpload,
    bannerUpload,
    isUploading: avatarUpload.isUploading || bannerUpload.isUploading,
    isSaving: updateMutation.isPending,
    handleSave,
  };
};

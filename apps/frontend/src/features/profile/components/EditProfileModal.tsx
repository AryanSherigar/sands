import React, { useState } from "react";
import { IconAlertCircle } from "@tabler/icons-react";
import { Button } from "@/shared/components/ui/Button";
import { Modal } from "@/shared/components/ui/Modal";
import { useEditProfileForm } from "../hooks/useEditProfileForm";
import { AvatarPicker } from "./editProfile/AvatarPicker";
import { BannerPicker } from "./editProfile/BannerPicker";
import { IdentityFields } from "./editProfile/IdentityFields";
import { SegmentedControl } from "./SegmentedControl/SegmentedControl";
import type { EditProfileModalProps } from "./EditProfileModal.types";

type EditSection = "details" | "avatar" | "banner";

const SECTION_OPTIONS: { value: EditSection; label: string }[] = [
  { value: "details", label: "Details" },
  { value: "avatar", label: "Avatar" },
  { value: "banner", label: "Banner" },
];

export const EditProfileModal: React.FC<EditProfileModalProps> = ({
  profile,
  isOpen,
  onClose,
}) => {
  const [section, setSection] = useState<EditSection>("details");
  const form = useEditProfileForm(profile, onClose);
  const { draft, updateDraft } = form;

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Edit profile" isSheetOnMobile>
      <form onSubmit={form.handleSave} className="space-y-5">
        <SegmentedControl
          ariaLabel="Edit sections"
          options={SECTION_OPTIONS}
          value={section}
          onChange={setSection}
        />
        {form.errorMessage && (
          <p role="alert" className="flex items-center gap-2 text-xs text-danger">
            <IconAlertCircle size={16} stroke={1.5} aria-hidden="true" />
            {form.errorMessage}
          </p>
        )}
        {section === "details" && (
          <IdentityFields
            displayName={draft.displayName}
            bio={draft.bio}
            onDisplayNameChange={(displayName) => updateDraft({ displayName })}
            onBioChange={(bio) => updateDraft({ bio })}
          />
        )}
        {section === "avatar" && (
          <AvatarPicker
            selectedUrl={draft.avatarUrl}
            isUploading={form.isUploading}
            onSelect={(avatarUrl) => updateDraft({ avatarUrl })}
            onFileChange={form.avatarUpload.handleFileChange}
          />
        )}
        {section === "banner" && (
          <BannerPicker
            selectedUrl={draft.bannerUrl}
            isUploading={form.isUploading}
            onSelect={(bannerUrl) => updateDraft({ bannerUrl })}
            onFileChange={form.bannerUpload.handleFileChange}
          />
        )}
        <div className="flex items-center justify-end gap-2 border-t border-border-subtle pt-4">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button
            type="submit"
            variant="primary"
            disabled={form.isSaving || form.isUploading}
          >
            {form.isSaving ? "Saving..." : "Save changes"}
          </Button>
        </div>
      </form>
    </Modal>
  );
};

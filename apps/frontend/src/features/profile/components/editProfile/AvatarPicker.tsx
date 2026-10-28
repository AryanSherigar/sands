import React from "react";
import { AVATAR_PRESETS } from "@/shared/constants/profile-presets";
import { ALLOWED_IMAGE_TYPES } from "../../constants/editProfile.constants";
import type { AvatarPickerProps } from "./AvatarPicker.types";

const FILE_INPUT_CLASSES =
  "block w-full cursor-pointer text-xs text-content-muted file:mr-4 file:rounded-sm file:border-0 file:bg-surface-raised file:px-3 file:py-2 file:text-xs file:font-medium file:text-content hover:file:bg-surface-overlay";

export const AvatarPicker: React.FC<AvatarPickerProps> = ({
  selectedUrl,
  isUploading,
  onSelect,
  onFileChange,
}) => (
  <div className="space-y-4">
    <div className="grid grid-cols-3 gap-3 sm:grid-cols-6">
      {AVATAR_PRESETS.map((preset) => {
        const isSelected = selectedUrl === preset.url;
        return (
          <button
            type="button"
            key={preset.id}
            aria-pressed={isSelected}
            onClick={() => onSelect(preset.url)}
            className={`flex flex-col items-center gap-1.5 rounded-md border p-2 transition duration-instant motion-reduce:transition-none ${
              isSelected
                ? "border-content bg-surface-raised"
                : "border-border-subtle hover:border-border-strong"
            }`}
          >
            <img
              src={preset.url}
              alt={preset.name}
              className="h-12 w-12 rounded-full object-cover"
            />
            <span className="w-full truncate text-center text-xs text-content-muted">
              {preset.name.split(" ")[0]}
            </span>
          </button>
        );
      })}
    </div>
    <div className="space-y-2 border-t border-border-subtle pt-3">
      <label htmlFor="edit-avatar-upload" className="text-xs text-content-muted">
        Upload a portrait (JPEG, PNG or WebP, under 5MB)
      </label>
      <input
        id="edit-avatar-upload"
        type="file"
        accept={ALLOWED_IMAGE_TYPES}
        onChange={onFileChange}
        disabled={isUploading}
        className={FILE_INPUT_CLASSES}
      />
    </div>
  </div>
);

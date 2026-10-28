import React from "react";
import { BANNER_PRESETS } from "@/shared/constants/profile-presets";
import { ALLOWED_IMAGE_TYPES } from "../../constants/editProfile.constants";
import type { BannerPickerProps } from "./BannerPicker.types";

const FILE_INPUT_CLASSES =
  "block w-full cursor-pointer text-xs text-content-muted file:mr-4 file:rounded-sm file:border-0 file:bg-surface-raised file:px-3 file:py-2 file:text-xs file:font-medium file:text-content hover:file:bg-surface-overlay";

export const BannerPicker: React.FC<BannerPickerProps> = ({
  selectedUrl,
  isUploading,
  onSelect,
  onFileChange,
}) => (
  <div className="space-y-4">
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
      {BANNER_PRESETS.map((preset) => {
        const isSelected = selectedUrl === preset.url;
        return (
          <button
            type="button"
            key={preset.id}
            aria-pressed={isSelected}
            onClick={() => onSelect(preset.url)}
            className={`overflow-hidden rounded-md border text-left transition duration-instant motion-reduce:transition-none ${
              isSelected
                ? "border-content"
                : "border-border-subtle hover:border-border-strong"
            }`}
          >
            <img
              src={preset.url}
              alt={preset.name}
              className="h-20 w-full object-cover"
            />
            <span className="block bg-surface-raised p-2">
              <span className="block text-xs font-medium text-content">
                {preset.name}
              </span>
              <span className="text-xs text-content-muted">
                {preset.description}
              </span>
            </span>
          </button>
        );
      })}
    </div>
    <div className="space-y-2 border-t border-border-subtle pt-3">
      <label htmlFor="edit-banner-upload" className="text-xs text-content-muted">
        Upload a banner (JPEG, PNG or WebP, under 5MB)
      </label>
      <input
        id="edit-banner-upload"
        type="file"
        accept={ALLOWED_IMAGE_TYPES}
        onChange={onFileChange}
        disabled={isUploading}
        className={FILE_INPUT_CLASSES}
      />
    </div>
  </div>
);

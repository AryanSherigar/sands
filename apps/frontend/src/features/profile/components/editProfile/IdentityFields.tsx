import React from "react";
import {
  BIO_MAX_LENGTH,
  DISPLAY_NAME_MAX_LENGTH,
} from "../../constants/editProfile.constants";
import type { IdentityFieldsProps } from "./IdentityFields.types";

const FIELD_CLASSES =
  "w-full rounded-sm border border-border-strong bg-surface-inset px-3 py-2 text-sm text-content placeholder:text-content-faint focus:border-content focus:outline-hidden focus:ring-[3px] focus:ring-content/20";

export const IdentityFields: React.FC<IdentityFieldsProps> = ({
  displayName,
  bio,
  onDisplayNameChange,
  onBioChange,
}) => (
  <div className="space-y-4">
    <div className="space-y-1.5">
      <label htmlFor="edit-display-name" className="text-xs text-content-muted">
        Display name
      </label>
      <input
        id="edit-display-name"
        type="text"
        maxLength={DISPLAY_NAME_MAX_LENGTH}
        value={displayName}
        onChange={(event) => onDisplayNameChange(event.target.value)}
        className={FIELD_CLASSES}
      />
    </div>
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <label htmlFor="edit-bio" className="text-xs text-content-muted">
          Bio
        </label>
        <span className="font-mono text-xs text-content-faint">
          {bio.length}/{BIO_MAX_LENGTH}
        </span>
      </div>
      <textarea
        id="edit-bio"
        rows={4}
        maxLength={BIO_MAX_LENGTH}
        value={bio}
        onChange={(event) => onBioChange(event.target.value)}
        className={FIELD_CLASSES}
      />
    </div>
  </div>
);

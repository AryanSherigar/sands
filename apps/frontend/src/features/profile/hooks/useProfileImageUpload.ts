import { useState } from "react";

export interface UseProfileImageUploadOptions {
  upload: (file: File) => Promise<string>;
  onUploaded: (url: string) => void;
  onError: (message: string | null) => void;
  failureMessage: string;
}

export const useProfileImageUpload = ({
  upload,
  onUploaded,
  onError,
  failureMessage,
}: UseProfileImageUploadOptions) => {
  const [isUploading, setIsUploading] = useState(false);

  const handleFileChange = async (
    event: React.ChangeEvent<HTMLInputElement>,
  ) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setIsUploading(true);
    onError(null);
    try {
      onUploaded(await upload(file));
    } catch {
      onError(failureMessage);
    } finally {
      setIsUploading(false);
      event.target.value = "";
    }
  };

  return { isUploading, handleFileChange };
};

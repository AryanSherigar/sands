import type { ContentTag } from "@/shared/constants/content-tags";

export interface ContentTagPickerProps {
  value: string | null;
  onChange: (tag: ContentTag) => void;
  disabled?: boolean;
  label?: string;
  description?: string;
}

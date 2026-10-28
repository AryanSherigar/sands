import type { SignInTriggerCopy } from "@/shared/constants/sign-in-triggers";

export interface SignInPanelProps {
  copy: SignInTriggerCopy;
  onSignedIn: () => void;
}

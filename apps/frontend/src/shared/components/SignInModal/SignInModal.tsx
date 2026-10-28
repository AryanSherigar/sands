import React from "react";
import { Modal } from "@/shared/components/ui/Modal";
import { SIGN_IN_TRIGGER_COPY } from "@/shared/constants/sign-in-triggers";
import { useSignInModalStore } from "@/shared/stores/signInModal.store";
import { SignInPanel } from "./SignInPanel";

export const SignInModal: React.FC = () => {
  const trigger = useSignInModalStore((state) => state.trigger);
  const settle = useSignInModalStore((state) => state.settle);

  if (!trigger) return null;
  const copy = SIGN_IN_TRIGGER_COPY[trigger];

  return (
    <Modal
      isOpen
      onClose={() => settle(false)}
      title={copy.title}
      isDismissible={copy.isDismissible}
      size="narrow"
      isSheetOnMobile
    >
      <SignInPanel copy={copy} onSignedIn={() => settle(true)} />
    </Modal>
  );
};

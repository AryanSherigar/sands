import React from "react";
import { Link } from "react-router-dom";
import { useAuth } from "@/features/auth/hooks/useAuth";
import { SIGN_IN_PATH } from "@/shared/constants/navigation";
import { IconUser } from "@tabler/icons-react";
import { AvatarMenu } from "./AvatarMenu";

export const AccountSlot: React.FC = () => {
  const { user, isLoading, logout } = useAuth();

  if (isLoading) {
    return (
      <div
        aria-hidden="true"
        className="h-8 w-8 animate-pulse rounded-full bg-surface-overlay"
      />
    );
  }
  if (!user) {
    return (
      <div className="flex items-center gap-3">
        <Link
          to={SIGN_IN_PATH}
          className="inline-flex h-9 items-center justify-center rounded-lg border border-border-strong bg-surface-raised px-4 font-sans text-sm font-medium text-content transition-colors hover:bg-surface-overlay hover:text-primary focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-accent"
        >
          Sign in
        </Link>
        <div
          aria-hidden="true"
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary text-primary-contrast"
        >
          <IconUser size={18} />
        </div>
      </div>
    );
  }
  return <AvatarMenu user={user} onSignOut={() => void logout()} />;
};

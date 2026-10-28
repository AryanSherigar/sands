import React from "react";
import { useNavigate } from "react-router-dom";
import { IconBrandGoogle, IconLogout } from "@tabler/icons-react";
import { useAuth } from "@/features/auth/hooks/useAuth";
import { Button } from "@/shared/components/ui/Button";
import { auth } from "@/shared/lib/firebase";
import { useMemberSince } from "../../hooks/useMemberSince";
import { REDO_SETUP_PATH } from "../../constants/settings.constants";

export const AccountSection: React.FC = () => {
  const navigate = useNavigate();
  const { logout } = useAuth();
  const memberSince = useMemberSince();
  const email = auth.currentUser?.email ?? "";

  const handleSignOut = async (): Promise<void> => {
    await logout();
    navigate("/", { replace: true });
  };

  return (
    <div className="space-y-4 rounded-md border border-border-subtle bg-surface-raised p-5">
      <div className="space-y-2">
        <label htmlFor="account-email" className="block font-sans text-xs font-medium text-content-muted">
          Signed-in email
        </label>
        <div className="flex items-center gap-3">
          <input
            id="account-email"
            readOnly
            value={email}
            className="h-10 min-w-0 flex-1 rounded-sm border border-border-strong bg-surface-inset px-3 font-mono text-sm text-content"
          />
          <span className="inline-flex shrink-0 items-center gap-1.5 rounded-sm border border-border-strong px-2 py-1 font-sans text-xs text-content-muted">
            <IconBrandGoogle size={16} stroke={1.5} aria-hidden="true" />
            Google
          </span>
        </div>
      </div>
      {memberSince && (
        <p className="border-t border-border-subtle pt-4 font-sans text-xs text-content-faint">
          Member since {memberSince}
        </p>
      )}
      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border-subtle pt-4">
        <Button variant="secondary" onClick={() => navigate(REDO_SETUP_PATH)}>
          Redo setup
        </Button>
        <Button variant="ghost" onClick={() => void handleSignOut()}>
          <IconLogout size={16} stroke={1.5} aria-hidden="true" />
          Sign out
        </Button>
      </div>
    </div>
  );
};

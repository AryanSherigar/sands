import { create } from "zustand";
import { UserResponse } from "../types/auth.types";

interface AuthState {
  accessToken: string | null;
  user: UserResponse | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  isSuspended: boolean;
  setAuth: (token: string, user: UserResponse) => void;
  patchUser: (patch: Partial<UserResponse>) => void;
  logout: () => void;
  markSuspended: () => void;
  setLoading: (status: boolean) => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  accessToken: null,
  user: null,
  isAuthenticated: false,
  isLoading: true,
  isSuspended: false,
  setAuth: (token, user) =>
    set({
      accessToken: token,
      user,
      isAuthenticated: true,
      isSuspended: false,
    }),
  patchUser: (patch) =>
    set((state) => ({ user: state.user ? { ...state.user, ...patch } : null })),
  logout: () => set({ accessToken: null, user: null, isAuthenticated: false }),
  markSuspended: () =>
    set({
      accessToken: null,
      user: null,
      isAuthenticated: false,
      isSuspended: true,
    }),
  setLoading: (status) => set({ isLoading: status }),
}));

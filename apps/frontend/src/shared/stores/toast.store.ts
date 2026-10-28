import { create } from "zustand";
import type {
  ToastAction,
  ToastItem,
  ToastKind,
} from "@/shared/types/toast.types";

interface ToastState {
  queue: ToastItem[];
  showToast: (message: string, kind?: ToastKind, action?: ToastAction) => void;
  dismissToast: (id: number) => void;
}

let nextToastId = 1;

export const useToastStore = create<ToastState>((set) => ({
  queue: [],
  showToast: (message, kind = "info", action) =>
    set((state) => ({
      queue: [...state.queue, { id: nextToastId++, message, kind, action }],
    })),
  dismissToast: (id) =>
    set((state) => ({ queue: state.queue.filter((item) => item.id !== id) })),
}));

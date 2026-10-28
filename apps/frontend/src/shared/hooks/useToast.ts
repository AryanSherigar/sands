import { useToastStore } from "@/shared/stores/toast.store";

export const useToast = () => useToastStore((state) => state.showToast);

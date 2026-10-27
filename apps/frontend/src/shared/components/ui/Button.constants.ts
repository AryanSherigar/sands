export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger" | "accent";
export type ButtonSize = "sm" | "md" | "lg";

export const BUTTON_BASE_CLASSES =
  "inline-flex items-center justify-center gap-2 font-sans font-medium rounded-md transition duration-base ease-motion-enter focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-surface active:translate-y-px disabled:opacity-40 disabled:cursor-not-allowed disabled:active:translate-y-0";

export const VARIANT_CLASSES: Record<ButtonVariant, string> = {
  primary: "bg-primary text-primary-contrast font-semibold hover:bg-primary/90",
  secondary:
    "bg-surface-raised text-content border border-border-strong hover:bg-surface-overlay hover:border-content-muted",
  ghost:
    "bg-transparent text-content-muted hover:text-content hover:bg-white/6",
  danger:
    "bg-transparent text-danger border border-danger/30 hover:bg-danger/10 hover:border-danger",
  accent:
    "bg-transparent text-accent border border-accent hover:bg-accent/10",
};

export const SIZE_CLASSES: Record<ButtonSize, string> = {
  sm: "h-8 px-3 text-xs",
  md: "h-10 px-4 text-sm",
  lg: "h-12 px-6 text-base",
};

interface TabEmptyStateAction {
  label: string;
  to: string;
}

export interface TabEmptyStateProps {
  message: string;
  action?: TabEmptyStateAction;
}

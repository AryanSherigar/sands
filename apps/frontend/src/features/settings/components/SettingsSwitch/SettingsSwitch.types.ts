export interface SettingsSwitchProps {
  id: string;
  label: string;
  description?: string;
  isChecked: boolean;
  isDisabled?: boolean;
  onChange: (isChecked: boolean) => void;
}

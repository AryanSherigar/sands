export interface GenerateMapFormProps {
  initialDescription: string;
  isBusy: boolean;
  stageLabel: string | null;
  errorMessage: string | null;
  onGenerate: (description: string) => void;
}

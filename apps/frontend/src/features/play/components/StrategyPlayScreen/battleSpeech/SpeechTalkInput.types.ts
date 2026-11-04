export interface SpeechTalkInputProps {
  playthroughId: string;
  talkLabel: string;
  isSubmitting: boolean;
  onSubmit: (text: string) => void;
}

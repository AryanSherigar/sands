// Mirrors apps/core-api/app/models/client_effect.py: one-shot effects a
// scenario condition asks the client to play after a turn commits.

export interface InputTakeoverParams {
  text: string;
  lock_ms: number;
  type_ms_per_char: number;
}

export interface PhoneEchoParams {
  record_ms: number;
  delay_ms: number;
}

export type ClientEffect =
  | { kind: "input_takeover"; params: InputTakeoverParams }
  | { kind: "phone_echo"; params: PhoneEchoParams };

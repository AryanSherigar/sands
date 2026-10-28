import type {
  ClientEffect,
  InputTakeoverParams,
  PhoneEchoParams,
} from "./clientEffects.types";

type Fields = Record<string, unknown>;

const isFields = (value: unknown): value is Fields =>
  typeof value === "object" && value !== null;

const isNumberField = (fields: Fields, key: string): boolean =>
  typeof fields[key] === "number";

function readTakeover(params: Fields): InputTakeoverParams | null {
  const isValid =
    typeof params.text === "string" &&
    isNumberField(params, "lock_ms") &&
    isNumberField(params, "type_ms_per_char");
  return isValid ? (params as unknown as InputTakeoverParams) : null;
}

function readEcho(params: Fields): PhoneEchoParams | null {
  const isValid = isNumberField(params, "record_ms") && isNumberField(params, "delay_ms");
  return isValid ? (params as unknown as PhoneEchoParams) : null;
}

function toEffect(payload: Fields): ClientEffect | null {
  if (!isFields(payload.params)) return null;
  if (payload.kind === "input_takeover") {
    const params = readTakeover(payload.params);
    return params ? { kind: "input_takeover", params } : null;
  }
  if (payload.kind === "phone_echo") {
    const params = readEcho(payload.params);
    return params ? { kind: "phone_echo", params } : null;
  }
  return null;
}

/** Null (with a warning) for anything this client cannot play. */
export function parseClientEffect(data: string): ClientEffect | null {
  try {
    const payload: unknown = JSON.parse(data);
    const effect = isFields(payload) ? toEffect(payload) : null;
    if (!effect) console.warn("Ignoring unplayable client effect", data);
    return effect;
  } catch (error: unknown) {
    console.warn("Malformed client effect payload", error);
    return null;
  }
}

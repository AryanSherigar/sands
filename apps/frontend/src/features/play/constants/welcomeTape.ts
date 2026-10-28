export const WELCOME_ASSET_ROOT = "/welcome-tapes/tallis-v1/";
export const WELCOME_MEDIA_TIMEOUT = 20000;
export const WELCOME_VOICE_TIMEOUT = 15000;
export const WELCOME_BODY_SECONDS = 1294 / 30;
export const WELCOME_HOLD_SECONDS = 2;
export const WELCOME_BLACK_SECONDS = 0.5;
export const WELCOME_CAPTIONS = [
  [3, 280 / 30, "Welcome to Tallis. You have been assigned to the Night Records Desk on Floor Nine."],
  [334 / 30, 459 / 30, "I'm Katie. This recording will introduce you to your duties."],
  [513 / 30, 737 / 30, "During your shift, you will receive visitors and maintain the Log. The desk has been prepared for your arrival."],
  [791 / 30, 984 / 30, "Every visitor signs the Log. Record the time they give you, not the time on the wall."],
  [1038 / 30, 1240 / 30, "Your standing instructions are on the desk. Please read them before eleven, and again at one."],
] as const;

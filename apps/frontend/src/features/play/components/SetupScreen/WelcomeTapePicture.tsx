import { useRef } from "react";
import { useIsMotionReduced } from "@/shared/hooks/useIsMotionReduced";
import { WELCOME_ASSET_ROOT, WELCOME_BODY_SECONDS, WELCOME_CAPTIONS } from "../../constants/welcomeTape";
import { useWelcomeVideo } from "../../hooks/useWelcomeVideo";
import type { WelcomeTapePictureProps } from "./WelcomeTapePicture.types";

export function WelcomeTapePicture(props: WelcomeTapePictureProps) {
  const isReducedMotion = useIsMotionReduced();
  const video = useRef<HTMLVideoElement>(null);
  const isClosing = props.time >= 1 + WELCOME_BODY_SECONDS;
  const isBlack = props.controller !== null && props.time >= props.controller.duration - 0.5;
  const picture = getPicture(props.urls, props.time);
  const caption = getCaption(props.time, props.characterName);
  useWelcomeVideo(video, props.time, props.isPaused, picture);
  return <div className={`welcome-frame overflow-hidden ${isBlack ? "welcome-black" : ""}`}>
    {!isClosing && !isReducedMotion && <video ref={video} src={picture} muted playsInline loop={props.time < 0} autoPlay={props.time < 0} className="h-full w-full object-cover" onWaiting={() => { if (video.current && video.current.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) props.onBuffer(); }} onCanPlay={props.onReady} onError={props.onError} />}
    {(isClosing || isReducedMotion) && !isBlack && <div className="welcome-portrait">
      <img src={props.urls[2] || `${WELCOME_ASSET_ROOT}katie.png`} alt="Katie, Personnel Services" />
      {isClosing && !isReducedMotion && props.controller?.mouthIsOpen && <img src={props.urls[3]} alt="" className="welcome-mouth" />}
      {isClosing && !isReducedMotion && hasBlink(props.time) && <img src={props.urls[3]} alt="" className="welcome-blink" />}
    </div>}
    {isClosing && !isBlack && <p className="absolute bottom-[5.7%] left-[25.3%] font-mono text-[clamp(12px,2vw,29px)]">KATIE · Personnel Services</p>}
    {!isBlack && <div className="welcome-scanlines" />}
    {props.hasCaptions && !isBlack && <p aria-live="off" className="absolute bottom-20 left-4 right-4 bg-black/80 p-2 text-center font-mono text-sm">{caption}</p>}
  </div>;
}

function getPicture(urls: string[], time: number): string {
  if (time < 0) return `${WELCOME_ASSET_ROOT}static.mp4`;
  return time < 1 ? urls[0] : urls[1];
}

function getCaption(time: number, name: string): string {
  if (time >= 1 + WELCOME_BODY_SECONDS) return name ? `Thank you for your service, ${name}.` : "Thank you for your service.";
  return WELCOME_CAPTIONS.find(([start, end]) => time - 1 >= start && time - 1 < end)?.[2] ?? "";
}

function hasBlink(time: number): boolean {
  const frame = Math.floor(time * 30) % 157;
  return frame >= 119 && frame <= 122;
}

import type { WelcomeTapeControlsProps } from "./WelcomeTapeControls.types";

export function WelcomeTapeControls(props: WelcomeTapeControlsProps) {
  return <div className="absolute inset-x-0 bottom-0 flex flex-wrap items-center justify-center gap-4 bg-linear-to-t from-black/80 to-transparent p-3 font-mono text-sm">
    {props.isFailed && <><span role="alert">Tape could not load.</span><button onClick={props.onRetry}>Retry</button></>}
    {props.isReady && <button onClick={props.isPaused ? props.onPlay : props.onPause}>{props.isPaused ? "Play tape" : "Pause"}</button>}
    <button onClick={props.onMute}>{props.isMuted ? "Unmute" : "Mute"}</button>
    <button aria-pressed={props.hasCaptions} onClick={props.onCaptions}>Captions</button>
    <button onClick={props.onSkip}>{props.isFailed ? "Continue to story" : "Skip tape"}</button>
  </div>;
}

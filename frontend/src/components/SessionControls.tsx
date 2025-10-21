import { useEffect, useState } from "react";
import { useConnectionState, useRoomContext } from "@livekit/components-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type SessionControlsProps = {
  onLeave: () => void;
};

const SessionControls = ({ onLeave }: SessionControlsProps) => {
  const room = useRoomContext();
  const [ending, setEnding] = useState(false);
  const [audioStarted, setAudioStarted] = useState(false);
  const [microphoneEnabled, setMicrophoneEnabled] = useState<boolean>(true);
  const connectionState = useConnectionState();

  useEffect(() => {
    const local = room?.localParticipant;
    if (!local) {
      return;
    }
    setMicrophoneEnabled(local.isMicrophoneEnabled);
    if (local.isCameraEnabled) {
      void local.setCameraEnabled(false);
    }
  }, [room]);

  const handleLeave = async () => {
    if (ending) return;
    if (!room) {
      onLeave();
      return;
    }
    setEnding(true);
    try {
      if (connectionState === "connected" || connectionState === "reconnecting") {
        await room.disconnect();
      }
    } finally {
      setEnding(false);
      onLeave();
    }
  };

  const handleStartAudio = async () => {
    if (audioStarted) return;
    if (!room) return;
    try {
      await room.startAudio();
      setAudioStarted(true);
    } catch (error) {
      console.error("Failed to start audio playback", error);
    }
  };

  const toggleMicrophone = async () => {
    if (!room) return;
    try {
      const newState = !microphoneEnabled;
      await room.localParticipant.setMicrophoneEnabled(newState);
      setMicrophoneEnabled(newState);
    } catch (error) {
      console.error("Failed to toggle microphone", error);
    }
  };

  return (
    <footer className="mt-6 border-t border-white/15 pt-4">
      <div className="flex flex-wrap items-center justify-end gap-3">
        <Button
          type="button"
          variant={audioStarted ? "outline" : "default"}
          onClick={handleStartAudio}
          disabled={audioStarted}
          className={cn("min-w-[140px]")}
        >
          {audioStarted ? "Audio Ready" : "Enable Audio"}
        </Button>
        <Button
          type="button"
          variant="ghost"
          onClick={toggleMicrophone}
          aria-live="polite"
          className="min-w-[140px] text-white"
        >
          <span aria-hidden="true" className="mr-2 text-base">
            {microphoneEnabled ? "🎙️" : "🔇"}
          </span>
          {microphoneEnabled ? "Mute Mic" : "Unmute Mic"}
        </Button>
        <Button
          type="button"
          variant="destructive"
          onClick={handleLeave}
          disabled={ending}
          className="min-w-[140px]"
        >
          {ending ? "Ending…" : "End Call"}
        </Button>
      </div>
    </footer>
  );
};

export default SessionControls;

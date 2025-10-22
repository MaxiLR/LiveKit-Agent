import { useEffect, useState } from "react";
import {
  useAudioPlayback,
  useConnectionState,
  useRoomContext
} from "@livekit/components-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type SessionControlsProps = {
  onLeave: () => void;
};

const SessionControls = ({ onLeave }: SessionControlsProps) => {
  const room = useRoomContext();
  const [ending, setEnding] = useState(false);
  const [microphoneEnabled, setMicrophoneEnabled] = useState<boolean>(true);
  const connectionState = useConnectionState();
  const { canPlayAudio, startAudio } = useAudioPlayback(room ?? undefined);
  const [isStartingAudio, setIsStartingAudio] = useState(false);

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
        {!canPlayAudio && (
          <Button
            type="button"
            variant="default"
            onClick={async () => {
              if (isStartingAudio) return;
              setIsStartingAudio(true);
              try {
                await startAudio();
              } catch (error) {
                console.error("Failed to start audio playback", error);
              } finally {
                setIsStartingAudio(false);
              }
            }}
            disabled={isStartingAudio}
            className={cn("min-w-[140px]")}
          >
            {isStartingAudio ? "Enabling…" : "Enable Audio"}
          </Button>
        )}
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

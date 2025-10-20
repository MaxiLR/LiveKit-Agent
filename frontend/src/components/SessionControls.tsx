import { useEffect, useState } from "react";
import { useConnectionState, useRoomContext } from "@livekit/components-react";

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
    if (ending) {
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
    if (audioStarted) {
      return;
    }
    try {
      await room.startAudio();
      setAudioStarted(true);
    } catch (error) {
      console.error("Failed to start audio playback", error);
    }
  };

  const toggleMicrophone = async () => {
    try {
      const newState = !microphoneEnabled;
      await room.localParticipant.setMicrophoneEnabled(newState);
      setMicrophoneEnabled(newState);
    } catch (error) {
      console.error("Failed to toggle microphone", error);
    }
  };

  return (
    <footer className="session-controls">
      <div className="controls-row">
        <button
          type="button"
          className="btn secondary"
          onClick={handleStartAudio}
          disabled={audioStarted}
        >
          {audioStarted ? "Audio Ready" : "Enable Audio"}
        </button>

        <button
          type="button"
          className="btn secondary"
          onClick={toggleMicrophone}
        >
          {microphoneEnabled ? "Mute Mic" : "Unmute Mic"}
        </button>

        <button
          type="button"
          className="btn danger"
          onClick={handleLeave}
          disabled={ending}
        >
          {ending ? "Ending…" : "End Call"}
        </button>
      </div>
    </footer>
  );
};

export default SessionControls;

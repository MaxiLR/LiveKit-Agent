import { useCallback, useMemo, useState } from "react";
import {
  LiveKitRoom,
  RoomAudioRenderer,
  useConnectionState
} from "@livekit/components-react";
import "@livekit/components-styles";

import JoinForm, { type JoinFormValues } from "./components/JoinForm";
import SessionControls from "./components/SessionControls";
import TranscriptPanel from "./components/TranscriptPanel";

const TOKEN_ENDPOINT_PATH = "/api/livekit/token";

const serverUrl = import.meta.env.VITE_LIVEKIT_WS_URL as string | undefined;
const backendUrl = import.meta.env.VITE_BACKEND_URL as string | undefined;

const App = () => {
  const [token, setToken] = useState<string>();
  const [identity, setIdentity] = useState<string>();
  const [roomName, setRoomName] = useState<string>("saveapp-story-room");
  const [joinError, setJoinError] = useState<string>();
  const [isJoining, setIsJoining] = useState(false);

  const joinDisabledReason = !serverUrl
    ? "Missing VITE_LIVEKIT_WS_URL value."
    : !backendUrl
      ? "Missing VITE_BACKEND_URL value."
      : undefined;

  const handleJoin = useCallback(
    async ({ displayName, room }: JoinFormValues) => {
      if (!serverUrl || !backendUrl) {
        setJoinError(
          "Frontend is missing configuration. Check VITE_LIVEKIT_WS_URL and VITE_BACKEND_URL."
        );
        return;
      }
      setJoinError(undefined);
      setIsJoining(true);
      try {
        const sanitizedRoom = room.trim();
        const sanitizedName = displayName.trim();
        const fetchedToken = await requestAccessToken({
          identity: sanitizedName,
          roomName: sanitizedRoom
        });
        setIdentity(sanitizedName);
        setRoomName(sanitizedRoom);
        setToken(fetchedToken);
      } catch (error) {
        setJoinError(
          error instanceof Error ? error.message : "Failed to start the call."
        );
      } finally {
        setIsJoining(false);
      }
    },
    []
  );

  const handleLeave = useCallback(() => {
    setToken(undefined);
  }, []);

  if (!serverUrl || !backendUrl) {
    return (
      <main className="app-shell">
        <section className="card warning">
          <h1>Frontend configuration required</h1>
          <p>
            Set <code>VITE_LIVEKIT_WS_URL</code> and <code>VITE_BACKEND_URL</code>{" "}
            in <code>frontend/.env</code> before starting the app.
          </p>
        </section>
      </main>
    );
  }

  return (
    <main className="app-shell">
      {!token ? (
        <section className="card join-card">
          <header className="card-header">
            <h1>SaveApp Story Companion</h1>
            <p>
              Start a voice call with the SaveApp assistant and see the live
              transcript update in real time.
            </p>
          </header>
          <JoinForm
            defaultRoomName={roomName}
            onSubmit={handleJoin}
            isSubmitting={isJoining}
            error={joinError}
            disabledReason={joinDisabledReason}
          />
        </section>
      ) : (
        <div className="room-stage">
          <LiveKitRoom
            token={token}
            serverUrl={serverUrl}
            connectOptions={{ autoSubscribe: true }}
            onDisconnected={handleLeave}
            data-lk-theme="default"
          >
            <RoomAudioRenderer />
            <ActiveSession
              displayName={identity ?? "Guest"}
              roomName={roomName}
              onLeave={handleLeave}
            />
          </LiveKitRoom>
        </div>
      )}
    </main>
  );
};

type TokenRequest = {
  identity: string;
  roomName: string;
};

async function requestAccessToken({ identity, roomName }: TokenRequest) {
  const trimmedBackend = (backendUrl ?? "").replace(/\/+$/, "");
  if (!trimmedBackend) {
    throw new Error("Backend URL is not configured.");
  }
  const response = await fetch(`${trimmedBackend}${TOKEN_ENDPOINT_PATH}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ identity, room: roomName })
  });
  if (!response.ok) {
    const detail = await safeReadError(response);
    throw new Error(
      detail ?? `Token request failed with status ${response.status}.`
    );
  }
  const payload = (await response.json()) as { token?: string };
  if (!payload?.token) {
    throw new Error("Token response did not include a LiveKit access token.");
  }
  return payload.token;
}

async function safeReadError(response: Response) {
  try {
    const data = await response.json();
    if (typeof data?.detail === "string") {
      return data.detail;
    }
    if (typeof data?.error === "string") {
      return data.error;
    }
  } catch {
    // ignore
  }
  try {
    const text = await response.text();
    return text || undefined;
  } catch {
    return undefined;
  }
}

type ActiveSessionProps = {
  displayName: string;
  roomName: string;
  onLeave: () => void;
};

const ActiveSession = ({ displayName, roomName, onLeave }: ActiveSessionProps) => {
  return (
    <section className="session-layout">
      <header className="session-header">
        <div>
          <p className="eyebrow">Connected to</p>
          <h1 className="session-title">{roomName}</h1>
          <p className="session-subtitle">Speaking as {displayName}</p>
        </div>
        <ConnectionBadge />
      </header>

      <TranscriptPanel />

      <SessionControls onLeave={onLeave} />
    </section>
  );
};

const ConnectionBadge = () => {
  const connection = useConnectionState();

  const { label, tone } = useMemo(() => {
    switch (connection) {
      case "connected":
        return { label: "Live", tone: "success" as const };
      case "reconnecting":
        return { label: "Reconnecting…", tone: "warning" as const };
      case "connecting":
        return { label: "Connecting…", tone: "muted" as const };
      default:
        return { label: "Offline", tone: "danger" as const };
    }
  }, [connection]);

  return <span className={`status-pill ${tone}`}>{label}</span>;
};

export default App;

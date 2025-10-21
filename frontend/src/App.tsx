import {
  LiveKitRoom,
  RoomAudioRenderer,
  useConnectionState
} from "@livekit/components-react";
import "@livekit/components-styles";
import { useCallback, useEffect, useMemo, useState } from "react";

import JoinForm, { type JoinFormValues } from "@/components/JoinForm";
import KnowledgeSidebar from "@/components/KnowledgeSidebar";
import SessionControls from "@/components/SessionControls";
import TranscriptPanel from "@/components/TranscriptPanel";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from "@/components/ui/card";

const TOKEN_ENDPOINT_PATH = "/api/livekit/token";

const serverUrl = import.meta.env.VITE_LIVEKIT_WS_URL as string | undefined;
const backendUrl = import.meta.env.VITE_BACKEND_URL as string | undefined;
const ragServiceUrl = import.meta.env.VITE_RAG_SERVICE_URL as string | undefined;

type KnowledgeDocument = {
  filename: string;
  sizeBytes: number;
};

type DocumentListResponse = {
  documents?: Array<{ filename: string; size_bytes: number }>;
  vector_store_id?: string;
};

type DocumentIngestResponse = {
  document?: { filename: string; size_bytes: number };
  vector_store_id?: string;
  already_present?: boolean;
};

const App = () => {
  const [token, setToken] = useState<string>();
  const [identity, setIdentity] = useState<string>();
  const [roomName, setRoomName] = useState<string>("example-room");
  const [joinError, setJoinError] = useState<string>();
  const [isJoining, setIsJoining] = useState(false);

  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [vectorStoreId, setVectorStoreId] = useState<string>();
  const [documentsLoading, setDocumentsLoading] = useState(false);
  const [documentsError, setDocumentsError] = useState<string>();
  const [isUploading, setIsUploading] = useState(false);

  const ragBaseUrl = useMemo(
    () => (ragServiceUrl ? ragServiceUrl.replace(/\/+$/, "") : undefined),
    [ragServiceUrl]
  );

  const ragUnavailableMessage = ragBaseUrl
    ? undefined
    : "Set VITE_RAG_SERVICE_URL to enable document uploads.";

  const joinDisabledReason = !serverUrl
    ? "Missing VITE_LIVEKIT_WS_URL value."
    : !backendUrl
      ? "Missing VITE_BACKEND_URL value."
      : undefined;

  const refreshDocuments = useCallback(async () => {
    if (!ragBaseUrl) {
      setDocuments([]);
      setVectorStoreId(undefined);
      setDocumentsError(undefined);
      return;
    }

    setDocumentsLoading(true);
    setDocumentsError(undefined);
    try {
      const response = await fetch(`${ragBaseUrl}/documents`, {
        method: "GET"
      });
      if (!response.ok) {
        const detail = await safeReadError(response);
        throw new Error(
          detail ?? `Document list request failed with status ${response.status}.`
        );
      }

      const payload = (await response.json()) as DocumentListResponse;
      const normalized =
        payload.documents?.map((doc) => ({
          filename: doc.filename,
          sizeBytes: doc.size_bytes ?? 0
        })) ?? [];
      normalized.sort((a, b) => a.filename.localeCompare(b.filename));
      setDocuments(normalized);
      setVectorStoreId(payload.vector_store_id ?? undefined);
    } catch (error) {
      setDocumentsError(
        error instanceof Error ? error.message : "Failed to load documents."
      );
    } finally {
      setDocumentsLoading(false);
    }
  }, [ragBaseUrl]);

  useEffect(() => {
    void refreshDocuments();
  }, [refreshDocuments]);

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
    setIdentity(undefined);
  }, []);

  const handleUploadDocument = useCallback(
    async (file: File) => {
      if (!ragBaseUrl) {
        return;
      }
      setIsUploading(true);
      setDocumentsError(undefined);
      try {
        const formData = new FormData();
        formData.append("file", file);
        const response = await fetch(`${ragBaseUrl}/documents`, {
          method: "POST",
          body: formData
        });
        if (!response.ok) {
          const detail = await safeReadError(response);
          throw new Error(
            detail ?? `Upload failed with status ${response.status}.`
          );
        }
        const payload = (await response.json()) as DocumentIngestResponse;
        if (payload.vector_store_id) {
          setVectorStoreId(payload.vector_store_id);
        }
        if (payload.document) {
          setDocuments((current) => {
            const next = current.filter(
              (item) => item.filename !== payload.document?.filename
            );
            next.push({
              filename: payload.document.filename,
              sizeBytes: payload.document.size_bytes ?? 0
            });
            next.sort((a, b) => a.filename.localeCompare(b.filename));
            return next;
          });
        } else {
          await refreshDocuments();
        }
      } catch (error) {
        setDocumentsError(
          error instanceof Error ? error.message : "Failed to upload document."
        );
      } finally {
        setIsUploading(false);
      }
    },
    [ragBaseUrl, refreshDocuments]
  );

  if (!serverUrl || !backendUrl) {
    return (
      <main className="flex min-h-screen w-full items-center justify-center bg-black px-6 py-12 text-white">
        <Card className="w-full max-w-xl border border-white/30 bg-black text-white shadow-lg">
          <CardHeader>
            <CardTitle>Configuration Required</CardTitle>
            <CardDescription className="text-white/70">
              Provide <code className="font-mono text-white">VITE_LIVEKIT_WS_URL</code> and{" "}
              <code className="font-mono text-white">VITE_BACKEND_URL</code> in{" "}
              <code className="font-mono text-white">frontend/.env</code> before starting the app.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-white/60">
              Once the environment variables are set, refresh this page to continue.
            </p>
          </CardContent>
        </Card>
      </main>
    );
  }

  if (!token) {
    return (
      <main className="flex min-h-screen w-full items-center justify-center bg-black px-6 py-12 text-white">
        <Card className="w-full max-w-xl border border-white/30 bg-black text-white shadow-lg">
          <CardHeader>
            <CardTitle>LiveKit Knowledge Agent</CardTitle>
            <CardDescription className="text-white/70">
              Join a voice room to collaborate with the document-aware assistant.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <JoinForm
              defaultRoomName={roomName}
              onSubmit={handleJoin}
              isSubmitting={isJoining}
              error={joinError}
              disabledReason={joinDisabledReason}
            />
          </CardContent>
        </Card>
      </main>
    );
  }

  return (
    <main className="flex min-h-screen w-full items-center justify-center bg-black px-4 py-8 text-white">
      <div className="flex w-full max-w-6xl flex-col">
        <LiveKitRoom
          token={token}
          serverUrl={serverUrl}
          connectOptions={{ autoSubscribe: true }}
          onDisconnected={handleLeave}
          className="flex h-[82vh] flex-col rounded-[32px] border border-white/20 bg-black/80 px-8 py-6 shadow-2xl"
          data-lk-theme="default"
        >
          <RoomAudioRenderer />
          <ActiveSession
            displayName={identity ?? "Guest"}
            localIdentity={identity}
            roomName={roomName}
            documents={documents}
            vectorStoreId={vectorStoreId}
            documentsLoading={documentsLoading}
            documentsError={documentsError}
            onReloadDocuments={refreshDocuments}
            onUpload={handleUploadDocument}
            onLeave={handleLeave}
            isUploading={isUploading}
            ragUnavailableMessage={ragUnavailableMessage}
          />
        </LiveKitRoom>
      </div>
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
    throw new Error(detail ?? `Token request failed with status ${response.status}.`);
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
    if (typeof (data as { detail?: string }).detail === "string") {
      return (data as { detail?: string }).detail;
    }
    if (typeof (data as { error?: string }).error === "string") {
      return (data as { error?: string }).error;
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
  localIdentity?: string;
  roomName: string;
  documents: KnowledgeDocument[];
  vectorStoreId?: string;
  documentsLoading: boolean;
  documentsError?: string;
  onReloadDocuments: () => Promise<void> | void;
  onUpload: (file: File) => Promise<void> | void;
  onLeave: () => void;
  isUploading: boolean;
  ragUnavailableMessage?: string;
};

const ActiveSession = ({
  displayName,
  localIdentity,
  roomName,
  documents,
  vectorStoreId,
  documentsLoading,
  documentsError,
  onReloadDocuments,
  onUpload,
  onLeave,
  isUploading,
  ragUnavailableMessage
}: ActiveSessionProps) => {
  const connection = useConnectionState();

  const status = useMemo(() => {
    switch (connection) {
      case "connected":
        return { label: "Connected", className: "bg-white text-black" };
      case "reconnecting":
        return { label: "Reconnecting…", className: "border border-white/70 text-white" };
      case "disconnected":
        return { label: "Disconnected", className: "border border-white text-white" };
      default:
        return { label: connection ?? "Unknown", className: "border border-white/50 text-white" };
    }
  }, [connection]);

  return (
    <section className="flex h-full flex-1 flex-col">
      <header className="flex flex-col gap-4 border-b border-white/15 pb-4 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.35em] text-white/50">Room</p>
          <h1 className="text-2xl font-semibold tracking-tight text-white md:text-3xl">{roomName}</h1>
          <p className="text-sm text-white/60">Signed in as {displayName}</p>
        </div>
        <span className={`inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm ${status.className}`}>
          <span className="h-2 w-2 rounded-full bg-current" aria-hidden />
          {status.label}
        </span>
      </header>

      <div className="mt-6 flex flex-1 flex-col overflow-hidden">
        <div className="grid h-full flex-1 gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
          <div className="flex min-h-0 flex-col overflow-hidden rounded-2xl border border-white/20 bg-black/60 p-6">
            <TranscriptPanel localIdentity={localIdentity} />
          </div>
          <div className="flex min-h-0 flex-col overflow-hidden rounded-2xl border border-white/20 bg-black/60 p-6">
            <KnowledgeSidebar
              documents={documents}
              vectorStoreId={vectorStoreId}
              isLoading={documentsLoading}
              isUploading={isUploading}
              error={documentsError}
              onUpload={onUpload}
              onReload={onReloadDocuments}
              disabledMessage={ragUnavailableMessage}
            />
          </div>
        </div>
      </div>

      <SessionControls onLeave={onLeave} />
    </section>
  );
};

export default App;

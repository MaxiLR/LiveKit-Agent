import { FormEvent, useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

export type JoinFormValues = {
  displayName: string;
  room: string;
};

export type JoinFormProps = {
  defaultRoomName: string;
  onSubmit: (values: JoinFormValues) => Promise<void> | void;
  isSubmitting: boolean;
  error?: string;
  disabledReason?: string;
};

const JoinForm = ({
  defaultRoomName,
  onSubmit,
  isSubmitting,
  error,
  disabledReason
}: JoinFormProps) => {
  const [displayName, setDisplayName] = useState(() => buildDefaultName());
  const [roomName, setRoomName] = useState(defaultRoomName);
  const [formError, setFormError] = useState<string>();

  useEffect(() => {
    setRoomName(defaultRoomName);
  }, [defaultRoomName]);

  const blocked = useMemo(
    () => isSubmitting || Boolean(disabledReason),
    [disabledReason, isSubmitting]
  );

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmedName = displayName.trim();
    const trimmedRoom = roomName.trim();

    if (!trimmedName) {
      setFormError("Enter a display name to join the call.");
      return;
    }
    if (!trimmedRoom) {
      setFormError("Provide a room name.");
      return;
    }

    setFormError(undefined);
    await onSubmit({ displayName: trimmedName, room: trimmedRoom });
  };

  const alert = formError ?? error ?? disabledReason;

  return (
    <form className="space-y-6" onSubmit={handleSubmit}>
      <div className="space-y-2">
        <Label htmlFor="displayName">Display name</Label>
        <Input
          id="displayName"
          name="displayName"
          placeholder="Your name"
          autoComplete="name"
          value={displayName}
          onChange={(event) => setDisplayName(event.target.value)}
          disabled={blocked}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="roomName">Room name</Label>
        <Input
          id="roomName"
          name="roomName"
          placeholder="voice-agent-room"
          autoComplete="off"
          value={roomName}
          onChange={(event) => setRoomName(event.target.value)}
          disabled={blocked}
        />
      </div>

      <Button type="submit" className="w-full" disabled={blocked}>
        {isSubmitting ? "Starting…" : "Start Call"}
      </Button>

      {alert ? (
        <p
          role="alert"
          className={cn(
            "rounded-lg border border-white/30 bg-white/10 px-4 py-3 text-sm text-white",
            "animate-in fade-in"
          )}
        >
          {alert}
        </p>
      ) : null}
    </form>
  );
};

function buildDefaultName() {
  const adjectives = ["Curious", "Brave", "Clever", "Bold", "Lively", "Bright"];
  const animals = ["Fox", "Otter", "Lynx", "Hawk", "Dolphin", "Sparrow"];
  const adjective = adjectives[Math.floor(Math.random() * adjectives.length)];
  const animal = animals[Math.floor(Math.random() * animals.length)];
  return `${adjective}${animal}`;
}

export default JoinForm;

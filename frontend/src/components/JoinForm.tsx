import { FormEvent, useEffect, useMemo, useState } from "react";
import clsx from "clsx";

export type JoinFormValues = {
  displayName: string;
  room: string;
};

type JoinFormProps = {
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

  const isDisabled = useMemo(
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

  return (
    <form className="join-form" onSubmit={handleSubmit}>
      <div className="input-group">
        <label htmlFor="displayName">Display name</label>
        <input
          id="displayName"
          name="displayName"
          placeholder="Your name"
          value={displayName}
          onChange={(event) => setDisplayName(event.target.value)}
          disabled={isDisabled}
          autoComplete="name"
        />
      </div>

      <div className="input-group">
        <label htmlFor="roomName">Room name</label>
        <input
          id="roomName"
          name="roomName"
          placeholder="saveapp-story-room"
          value={roomName}
          onChange={(event) => setRoomName(event.target.value)}
          disabled={isDisabled}
          autoComplete="off"
        />
      </div>

      <button
        type="submit"
        className={clsx("btn", "primary")}
        disabled={isDisabled}
      >
        {isSubmitting ? "Starting…" : "Start Call"}
      </button>

      {(formError || error || disabledReason) && (
        <p className="form-error">
          {formError || error || disabledReason}
        </p>
      )}
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

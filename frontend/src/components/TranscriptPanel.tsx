import { useEffect, useMemo, useRef } from "react";
import { useTranscriptions } from "@livekit/components-react";
import type { TextStreamData } from "@livekit/components-core";

const TranscriptPanel = () => {
  const segments = useTranscriptions();
  const scrollRef = useRef<HTMLDivElement>(null);

  const recentSegments = useMemo(() => {
    const merged = mergeSegments(segments);
    merged.sort((a, b) => a.createdAt - b.createdAt);
    return merged.slice(-200);
  }, [segments]);

  useEffect(() => {
    const container = scrollRef.current;
    if (!container) {
      return;
    }
    container.scrollTop = container.scrollHeight;
  }, [recentSegments]);

  return (
    <section className="transcript-panel">
      <header>
        <h2>Live Transcript</h2>
      </header>

      <div className="transcript-scroll" ref={scrollRef}>
        {recentSegments.length === 0 ? (
          <p className="transcript-placeholder">
            Start speaking to see the transcript update here.
          </p>
        ) : (
          recentSegments.map((segment) => (
            <article
              key={segment.id}
              className={`transcript-line ${segment.final ? "final" : "draft"}`}
            >
              <span className="speaker-label">
                {segment.speakerName ?? segment.speakerIdentity ?? "Unknown"}
              </span>
              <span className="transcript-text">{segment.text}</span>
            </article>
          ))
        )}
      </div>
    </section>
  );
};

type MergedSegment = {
  id: string;
  text: string;
  final: boolean;
  speakerName?: string;
  speakerIdentity?: string;
  createdAt: number;
};

const mergeSegments = (segments: TextStreamData[]): MergedSegment[] => {
  const bySegment = new Map<string, MergedSegment>();

  for (const segment of segments) {
    const timestampRaw = segment.timestamp;
    const timestamp = typeof timestampRaw === "number"
      ? timestampRaw
      : Number(timestampRaw) || Date.now();
    const segmentId =
      segment.streamInfo?.attributes?.["lk_segment_id"] ??
      segment.streamInfo?.id ??
      `${segment.timestamp ?? Date.now()}-${segment.participantIdentity ?? ""}`;

    const existing = bySegment.get(segmentId);
    const isFinal =
      segment.streamInfo?.attributes?.["lk_final"] === "true" ||
      segment.streamInfo?.attributes?.["lk.transcription_final"] === "true" ||
      Boolean(segment.final);

    const altCandidate =
      (segment as unknown as { alternatives?: Array<{ text?: string }> })
        .alternatives?.[0]?.text;
    const candidateText =
      segment.text ?? altCandidate ?? existing?.text ?? "";

    const payload: MergedSegment = {
      id: segmentId,
      text: candidateText,
      final: isFinal || existing?.final === true,
      speakerName:
        segment.participantInfo?.name ??
        existing?.speakerName,
      speakerIdentity:
        segment.participantIdentity ??
        segment.participantInfo?.identity ??
        existing?.speakerIdentity,
      createdAt: existing?.createdAt ?? timestamp
    };

    if (existing && !isFinal) {
      payload.text = candidateText;
    }

    bySegment.set(segmentId, payload);
  }

  return Array.from(bySegment.values());
};

export default TranscriptPanel;

import { useEffect, useMemo, useRef } from "react";
import { useTranscriptions } from "@livekit/components-react";
import type { TextStreamData } from "@livekit/components-core";

import { cn } from "@/lib/utils";

export type TranscriptPanelProps = {
  localIdentity?: string;
};

type MergedSegment = {
  id: string;
  text: string;
  final: boolean;
  speakerName?: string;
  speakerIdentity?: string;
  createdAt: number;
  order: number;
};

const TranscriptPanel = ({ localIdentity }: TranscriptPanelProps) => {
  const segments = useTranscriptions();
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  const recentSegments = useMemo(
    () => mergeSegments(segments).slice(-200),
    [segments]
  );

  useEffect(() => {
    const container = scrollContainerRef.current;
    if (!container) return;
    container.scrollTop = container.scrollHeight;
  }, [recentSegments]);

  return (
    <div className="flex h-full min-h-0 flex-col gap-4 text-white">
      <div>
        <h2 className="text-lg font-semibold text-white">Transcript</h2>
        <p className="text-xs text-white/60">Agent responses align left, your turns align right.</p>
      </div>

      <div
        ref={scrollContainerRef}
        className="flex-1 overflow-y-auto pr-2"
      >
        {recentSegments.length === 0 ? (
          <p className="rounded-xl border border-dashed border-white/20 bg-white/5 px-4 py-6 text-center text-sm text-white/60">
            Start speaking to see the live transcript.
          </p>
        ) : (
          <div className="flex flex-col gap-3">
            {recentSegments.map((segment) => {
              const isLocalSpeaker = Boolean(
                localIdentity && segment.speakerIdentity === localIdentity
              );
              const speakerLabel =
                segment.speakerName ??
                segment.speakerIdentity ??
                (isLocalSpeaker ? "You" : "Agent");

              return (
                <article
                  key={segment.id}
                  className={cn(
                    "max-w-[80%] space-y-1 rounded-2xl border border-white/15 bg-white/10 px-4 py-3 text-sm",
                    segment.final ? "opacity-100" : "opacity-70",
                    isLocalSpeaker
                      ? "self-end rounded-br-sm text-right"
                      : "self-start rounded-bl-sm"
                  )}
                >
                  <span className="text-xs font-semibold uppercase tracking-wide text-white/50">
                    {speakerLabel}
                  </span>
                  <p className="whitespace-pre-wrap text-base leading-relaxed text-white">{segment.text}</p>
                </article>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

const mergeSegments = (segments: TextStreamData[]): MergedSegment[] => {
  const bySegment = new Map<string, MergedSegment>();
  let nextOrder = 0;

  const orderedSegments = [...segments].sort((a, b) => {
    const timeA = getSegmentTime(a);
    const timeB = getSegmentTime(b);
    if (timeA !== timeB) return timeA - timeB;
    const seqA =
      Number(
        a.streamInfo?.attributes?.["lk_sequence"] ??
          a.streamInfo?.attributes?.["lk_segment_sequence"]
      ) || 0;
    const seqB =
      Number(
        b.streamInfo?.attributes?.["lk_sequence"] ??
          b.streamInfo?.attributes?.["lk_segment_sequence"]
      ) || 0;
    return seqA - seqB;
  });

  orderedSegments.forEach((segment) => {
    const timestamp = getSegmentTime(segment);
    const segmentId =
      segment.streamInfo?.attributes?.["lk_segment_id"] ??
      segment.streamInfo?.id ??
      `${segment.timestamp ?? Date.now()}-${segment.participantIdentity ?? ""}`;

    const existing = bySegment.get(segmentId);
    const isFinal =
      segment.streamInfo?.attributes?.["lk_final"] === "true" ||
      segment.streamInfo?.attributes?.["lk.transcription_final"] === "true" ||
      Boolean(segment.final);

    const altCandidate = (
      segment as unknown as { alternatives?: Array<{ text?: string }> }
    ).alternatives?.[0]?.text;
    const candidateText =
      segment.text ?? altCandidate ?? existing?.text ?? "";

    if (existing) {
      if (candidateText) existing.text = candidateText;
      if (isFinal) existing.final = true;
      const name = segment.participantInfo?.name ?? existing.speakerName;
      if (name) existing.speakerName = name;
      const identity =
        segment.participantIdentity ??
        segment.participantInfo?.identity ??
        existing.speakerIdentity;
      if (identity) existing.speakerIdentity = identity;
    } else {
      bySegment.set(segmentId, {
        id: segmentId,
        text: candidateText,
        final: isFinal,
        speakerName: segment.participantInfo?.name,
        speakerIdentity:
          segment.participantIdentity ?? segment.participantInfo?.identity,
        createdAt: timestamp,
        order: nextOrder++
      });
    }
  });

  return Array.from(bySegment.values()).sort((a, b) => {
    if (a.order !== undefined && b.order !== undefined) {
      return a.order - b.order;
    }
    return a.createdAt - b.createdAt;
  });
};

const getSegmentTime = (segment: TextStreamData): number => {
  const attributes = segment.streamInfo?.attributes ?? {};
  const attrTime =
    Number(attributes["lk_end_time"]) ||
    Number(attributes["lk_start_time"]) ||
    Number(attributes["lk_timestamp"]);
  if (attrTime && !Number.isNaN(attrTime)) return attrTime;
  if (typeof segment.timestamp === "number" && !Number.isNaN(segment.timestamp)) {
    return segment.timestamp;
  }
  return Date.now();
};

export default TranscriptPanel;

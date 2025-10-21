import { ChangeEvent, useRef } from "react";
import { Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";

export type KnowledgeDocument = {
  filename: string;
  sizeBytes: number;
};

type KnowledgeSidebarProps = {
  documents: KnowledgeDocument[];
  vectorStoreId?: string;
  isLoading: boolean;
  isUploading: boolean;
  error?: string;
  onUpload?: (file: File) => Promise<void> | void;
  onReload?: () => Promise<void> | void;
  disabledMessage?: string;
};

const KnowledgeSidebar = ({
  documents,
  vectorStoreId,
  isLoading,
  isUploading,
  error,
  onUpload,
  onReload,
  disabledMessage
}: KnowledgeSidebarProps) => {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const uploadDisabled = isUploading || Boolean(disabledMessage);

  const handleUploadClick = () => {
    if (uploadDisabled) return;
    fileInputRef.current?.click();
  };

  const handleFileChange = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      await onUpload?.(file);
    } finally {
      event.target.value = "";
    }
  };

  return (
    <aside className="flex h-full flex-col gap-4 text-white">
      <header className="flex flex-col gap-1">
        <h3 className="text-lg font-semibold text-white">Knowledge Base</h3>
        {vectorStoreId ? (
          <p className="text-xs text-white/50">Vector store: {vectorStoreId}</p>
        ) : (
          <p className="text-xs text-white/50">Documents synced with the agent's retrieval store.</p>
        )}
      </header>

      {error ? (
        <div className="rounded-lg border border-white/30 bg-white/10 px-4 py-3 text-xs text-white" role="alert">
          <p>{error}</p>
          {onReload ? (
            <Button
              type="button"
              variant="ghost"
              className="mt-2 h-8 px-2 text-xs text-white hover:bg-white/20"
              onClick={() => onReload()}
              disabled={isLoading}
            >
              Retry
            </Button>
          ) : null}
        </div>
      ) : null}

      {disabledMessage ? (
        <p className="text-xs text-white/60">{disabledMessage}</p>
      ) : null}

      <div className="flex-1 overflow-hidden">
        <div className="flex h-full flex-col gap-3 overflow-y-auto pr-2">
          {isLoading ? (
            Array.from({ length: 4 }).map((_, index) => (
              <div
                key={`skeleton-${index}`}
                className="h-16 animate-pulse rounded-xl border border-white/15 bg-white/10"
              />
            ))
          ) : documents.length === 0 ? (
            <p className="rounded-xl border border-dashed border-white/25 bg-white/5 px-4 py-6 text-center text-sm text-white/60">
              No documents available yet. Upload a PDF to populate the knowledge base.
            </p>
          ) : (
            documents.map((doc) => (
              <article
                key={doc.filename}
                className="rounded-xl border border-white/20 bg-black/40 px-4 py-3"
              >
                <p className="text-sm font-medium text-white">{doc.filename}</p>
                <p className="text-xs text-white/50">{formatSize(doc.sizeBytes)}</p>
              </article>
            ))
          )}
        </div>
      </div>

      <div className="flex flex-col gap-2">
        <Button
          type="button"
          variant="default"
          className="w-full"
          onClick={handleUploadClick}
          disabled={uploadDisabled}
        >
          {isUploading ? (
            <span className="flex items-center justify-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> Uploading…
            </span>
          ) : (
            "Upload PDF"
          )}
        </Button>
        <input
          ref={fileInputRef}
          type="file"
          accept="application/pdf"
          onChange={handleFileChange}
          hidden
        />
        <p className="text-xs text-white/50">Only PDF files are accepted. Maximum size 25&nbsp;MB.</p>
      </div>
    </aside>
  );
};

const formatSize = (size: number) => {
  if (!size) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  let value = size;
  let unitIndex = 0;
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }
  return `${value.toFixed(unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
};

export default KnowledgeSidebar;

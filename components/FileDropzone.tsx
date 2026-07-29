"use client";

import { useCallback, useState } from "react";
import { useDropzone, type FileRejection } from "react-dropzone";

// Browsers can hang or crash a tab parsing/rendering extremely large files
// client-side; reject before that happens instead of letting the tab freeze.
const DEFAULT_MAX_SIZE_BYTES = 150 * 1024 * 1024;

type Props = {
  onFiles: (files: File[]) => void;
  multiple?: boolean;
  accept?: Record<string, string[]>;
  label?: string;
  maxSizeBytes?: number;
};

export default function FileDropzone({
  onFiles,
  multiple = false,
  accept = { "application/pdf": [".pdf"] },
  label = "Drag & drop a PDF here, or click to choose",
  maxSizeBytes = DEFAULT_MAX_SIZE_BYTES,
}: Props) {
  const [error, setError] = useState<string | null>(null);

  const onDrop = useCallback(
    (accepted: File[], rejected: FileRejection[]) => {
      setError(rejected.length > 0 ? rejected[0].errors[0]?.message ?? "File rejected" : null);
      if (accepted.length > 0) onFiles(accepted);
    },
    [onFiles]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    multiple,
    accept,
    maxSize: maxSizeBytes,
  });

  return (
    <div>
      <div
        {...getRootProps()}
        className={`cursor-pointer rounded-xl border-2 border-dashed p-10 text-center transition-colors ${
          isDragActive
            ? "border-blue-500 bg-blue-50 dark:bg-blue-950/30"
            : "border-zinc-300 hover:border-zinc-400 dark:border-zinc-700 dark:hover:border-zinc-600"
        }`}
      >
        <input {...getInputProps()} />
        <p className="text-sm text-zinc-600 dark:text-zinc-400">{label}</p>
      </div>
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
    </div>
  );
}

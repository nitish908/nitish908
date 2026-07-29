"use client";

import { useState } from "react";
import FileDropzone from "@/components/FileDropzone";
import { compressPdf, type CompressQuality } from "@/lib/pdf/compress";
import { downloadBytes } from "@/lib/download";

const QUALITY_OPTIONS: { value: CompressQuality; label: string }[] = [
  { value: "low", label: "Smallest file (lower quality)" },
  { value: "medium", label: "Balanced" },
  { value: "high", label: "Best quality (larger file)" },
];

export default function CompressPage() {
  const [file, setFile] = useState<File | null>(null);
  const [quality, setQuality] = useState<CompressQuality>("medium");
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resultSize, setResultSize] = useState<number | null>(null);

  function handleFile(files: File[]) {
    setError(null);
    setResultSize(null);
    setFile(files[0] ?? null);
  }

  async function handleCompress() {
    if (!file) return;
    setWorking(true);
    setError(null);
    setResultSize(null);
    try {
      const bytes = await compressPdf(file, quality);
      setResultSize(bytes.length);
      downloadBytes(bytes, "compressed.pdf");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to compress PDF.");
    } finally {
      setWorking(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl px-6 py-16">
      <h1 className="text-3xl font-bold tracking-tight">Compress PDF</h1>
      <p className="mt-2 text-zinc-600 dark:text-zinc-400">
        Shrinks file size by re-rendering each page as an optimized image.
        Works best on scanned or image-heavy PDFs; text-heavy PDFs will lose
        selectable text.
      </p>

      <div className="mt-8">
        <FileDropzone onFiles={handleFile} />
      </div>

      {file && (
        <div className="mt-6 space-y-4">
          <p className="text-sm text-zinc-600 dark:text-zinc-400">
            Selected: {file.name} ({(file.size / 1024 / 1024).toFixed(2)} MB)
          </p>

          <div>
            <label className="block text-sm font-medium">Quality</label>
            <select
              value={quality}
              onChange={(e) => setQuality(e.target.value as CompressQuality)}
              className="mt-2 w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
            >
              {QUALITY_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={handleCompress}
            disabled={working}
            className="rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-40"
          >
            {working ? "Compressing…" : "Compress & Download"}
          </button>

          {resultSize !== null && (
            <p className="text-sm text-green-600">
              Done — new size: {(resultSize / 1024 / 1024).toFixed(2)} MB
            </p>
          )}
        </div>
      )}

      {error && <p className="mt-4 text-sm text-red-600">{error}</p>}
    </div>
  );
}

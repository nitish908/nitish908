"use client";

import { useState } from "react";
import FileDropzone from "@/components/FileDropzone";
import { watermarkPdf } from "@/lib/pdf/watermark";
import { downloadBytes } from "@/lib/download";

export default function WatermarkPage() {
  const [file, setFile] = useState<File | null>(null);
  const [text, setText] = useState("DRAFT");
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function handleFile(files: File[]) {
    setError(null);
    setFile(files[0] ?? null);
  }

  async function handleWatermark() {
    if (!file) return;
    if (!text.trim()) {
      setError("Enter watermark text.");
      return;
    }
    setWorking(true);
    setError(null);
    try {
      const bytes = await watermarkPdf(file, text.trim());
      downloadBytes(bytes, "watermarked.pdf");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to watermark PDF.");
    } finally {
      setWorking(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl px-6 py-16">
      <h1 className="text-3xl font-bold tracking-tight">Watermark PDF</h1>
      <p className="mt-2 text-zinc-600 dark:text-zinc-400">
        Stamp text diagonally across every page of your PDF.
      </p>

      <div className="mt-8">
        <FileDropzone onFiles={handleFile} />
      </div>

      {file && (
        <div className="mt-6 space-y-4">
          <p className="text-sm text-zinc-600 dark:text-zinc-400">Selected: {file.name}</p>

          <div>
            <label className="block text-sm font-medium">Watermark text</label>
            <input
              type="text"
              value={text}
              onChange={(e) => setText(e.target.value)}
              className="mt-2 w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
            />
          </div>

          <button
            onClick={handleWatermark}
            disabled={working}
            className="rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-40"
          >
            {working ? "Applying…" : "Watermark & Download"}
          </button>
        </div>
      )}

      {error && <p className="mt-4 text-sm text-red-600">{error}</p>}
    </div>
  );
}

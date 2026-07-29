"use client";

import { useState } from "react";
import FileDropzone from "@/components/FileDropzone";
import { extractPageRange, splitIntoPages } from "@/lib/pdf/split";
import { downloadBytes, downloadZip } from "@/lib/download";

export default function SplitPage() {
  const [file, setFile] = useState<File | null>(null);
  const [range, setRange] = useState("");
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function handleFile(files: File[]) {
    setError(null);
    setFile(files[0] ?? null);
  }

  async function handleExtractRange() {
    if (!file) return;
    if (!range.trim()) {
      setError("Enter a page range, e.g. 1-3,5");
      return;
    }
    setWorking(true);
    setError(null);
    try {
      const result = await extractPageRange(file, range);
      downloadBytes(result.bytes, result.name);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to split PDF.");
    } finally {
      setWorking(false);
    }
  }

  async function handleSplitAll() {
    if (!file) return;
    setWorking(true);
    setError(null);
    try {
      const results = await splitIntoPages(file);
      await downloadZip(results, "split-pages.zip");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to split PDF.");
    } finally {
      setWorking(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl px-6 py-16">
      <h1 className="text-3xl font-bold tracking-tight">Split PDF</h1>
      <p className="mt-2 text-zinc-600 dark:text-zinc-400">
        Extract a page range, or split every page into its own file.
      </p>

      <div className="mt-8">
        <FileDropzone onFiles={handleFile} />
      </div>

      {file && (
        <div className="mt-6 space-y-6">
          <p className="text-sm text-zinc-600 dark:text-zinc-400">Selected: {file.name}</p>

          <div>
            <label className="block text-sm font-medium">Extract page range</label>
            <div className="mt-2 flex gap-2">
              <input
                type="text"
                value={range}
                onChange={(e) => setRange(e.target.value)}
                placeholder="e.g. 1-3,5"
                className="flex-1 rounded-lg border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
              />
              <button
                onClick={handleExtractRange}
                disabled={working}
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-40"
              >
                Extract
              </button>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium">Or split into individual pages</label>
            <button
              onClick={handleSplitAll}
              disabled={working}
              className="mt-2 rounded-lg border border-zinc-300 px-4 py-2 text-sm font-medium hover:bg-zinc-50 disabled:opacity-40 dark:border-zinc-700 dark:hover:bg-zinc-900"
            >
              {working ? "Working…" : "Split all pages (.zip)"}
            </button>
          </div>
        </div>
      )}

      {error && <p className="mt-4 text-sm text-red-600">{error}</p>}
    </div>
  );
}

"use client";

import { useState } from "react";
import FileDropzone from "@/components/FileDropzone";
import { mergePdfs } from "@/lib/pdf/merge";
import { downloadBytes } from "@/lib/download";

export default function MergePage() {
  const [files, setFiles] = useState<File[]>([]);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function addFiles(newFiles: File[]) {
    setError(null);
    setFiles((prev) => [...prev, ...newFiles]);
  }

  function move(index: number, dir: -1 | 1) {
    setFiles((prev) => {
      const next = [...prev];
      const target = index + dir;
      if (target < 0 || target >= next.length) return prev;
      [next[index], next[target]] = [next[target], next[index]];
      return next;
    });
  }

  function remove(index: number) {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  }

  async function handleMerge() {
    if (files.length < 2) {
      setError("Add at least 2 PDF files to merge.");
      return;
    }
    setWorking(true);
    setError(null);
    try {
      const bytes = await mergePdfs(files);
      downloadBytes(bytes, "merged.pdf");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to merge PDFs.");
    } finally {
      setWorking(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl px-6 py-16">
      <h1 className="text-3xl font-bold tracking-tight">Merge PDF</h1>
      <p className="mt-2 text-zinc-600 dark:text-zinc-400">
        Combine multiple PDF files into one. Reorder them before merging.
      </p>

      <div className="mt-8">
        <FileDropzone onFiles={addFiles} multiple />
      </div>

      {files.length > 0 && (
        <ul className="mt-6 divide-y divide-zinc-200 rounded-lg border border-zinc-200 dark:divide-zinc-800 dark:border-zinc-800">
          {files.map((file, i) => (
            <li key={`${file.name}-${i}`} className="flex items-center justify-between gap-3 px-4 py-3">
              <span className="truncate text-sm">{file.name}</span>
              <div className="flex shrink-0 gap-2 text-sm">
                <button onClick={() => move(i, -1)} disabled={i === 0} className="disabled:opacity-30">
                  ↑
                </button>
                <button onClick={() => move(i, 1)} disabled={i === files.length - 1} className="disabled:opacity-30">
                  ↓
                </button>
                <button onClick={() => remove(i)} className="text-red-600">
                  Remove
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}

      {error && <p className="mt-4 text-sm text-red-600">{error}</p>}

      <button
        onClick={handleMerge}
        disabled={working || files.length < 2}
        className="mt-6 rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-40"
      >
        {working ? "Merging…" : "Merge & Download"}
      </button>
    </div>
  );
}

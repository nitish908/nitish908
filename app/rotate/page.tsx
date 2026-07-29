"use client";

import { useState } from "react";
import FileDropzone from "@/components/FileDropzone";
import { rotatePdf } from "@/lib/pdf/rotate";
import { downloadBytes } from "@/lib/download";

const ANGLES = [90, 180, 270] as const;

export default function RotatePage() {
  const [file, setFile] = useState<File | null>(null);
  const [angle, setAngle] = useState<(typeof ANGLES)[number]>(90);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function handleFile(files: File[]) {
    setError(null);
    setFile(files[0] ?? null);
  }

  async function handleRotate() {
    if (!file) return;
    setWorking(true);
    setError(null);
    try {
      const bytes = await rotatePdf(file, angle);
      downloadBytes(bytes, "rotated.pdf");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to rotate PDF.");
    } finally {
      setWorking(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl px-6 py-16">
      <h1 className="text-3xl font-bold tracking-tight">Rotate PDF</h1>
      <p className="mt-2 text-zinc-600 dark:text-zinc-400">
        Rotate every page in a PDF by 90, 180, or 270 degrees.
      </p>

      <div className="mt-8">
        <FileDropzone onFiles={handleFile} />
      </div>

      {file && (
        <div className="mt-6 space-y-4">
          <p className="text-sm text-zinc-600 dark:text-zinc-400">Selected: {file.name}</p>

          <div>
            <label className="block text-sm font-medium">Rotation</label>
            <div className="mt-2 flex gap-2">
              {ANGLES.map((a) => (
                <button
                  key={a}
                  onClick={() => setAngle(a)}
                  className={`rounded-lg border px-4 py-2 text-sm font-medium ${
                    angle === a
                      ? "border-blue-600 bg-blue-600 text-white"
                      : "border-zinc-300 hover:bg-zinc-50 dark:border-zinc-700 dark:hover:bg-zinc-900"
                  }`}
                >
                  {a}°
                </button>
              ))}
            </div>
          </div>

          <button
            onClick={handleRotate}
            disabled={working}
            className="rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-40"
          >
            {working ? "Rotating…" : "Rotate & Download"}
          </button>
        </div>
      )}

      {error && <p className="mt-4 text-sm text-red-600">{error}</p>}
    </div>
  );
}

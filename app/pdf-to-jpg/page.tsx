"use client";

import { useState } from "react";
import FileDropzone from "@/components/FileDropzone";
import { pdfToImages } from "@/lib/pdf/toImages";
import { downloadBytes, downloadZip } from "@/lib/download";

export default function PdfToJpgPage() {
  const [file, setFile] = useState<File | null>(null);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function handleFile(files: File[]) {
    setError(null);
    setFile(files[0] ?? null);
  }

  async function handleConvert() {
    if (!file) return;
    setWorking(true);
    setError(null);
    try {
      const images = await pdfToImages(file, { format: "jpeg" });
      if (images.length === 1) {
        downloadBytes(images[0].bytes, images[0].name, "image/jpeg");
      } else {
        await downloadZip(images, "pdf-pages.zip");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to convert PDF to JPG.");
    } finally {
      setWorking(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl px-6 py-16">
      <h1 className="text-3xl font-bold tracking-tight">PDF to JPG</h1>
      <p className="mt-2 text-zinc-600 dark:text-zinc-400">
        Export every page of a PDF as a JPG image. Multiple pages download as
        a zip.
      </p>

      <div className="mt-8">
        <FileDropzone onFiles={handleFile} />
      </div>

      {file && (
        <div className="mt-6 space-y-4">
          <p className="text-sm text-zinc-600 dark:text-zinc-400">Selected: {file.name}</p>

          <button
            onClick={handleConvert}
            disabled={working}
            className="rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-40"
          >
            {working ? "Converting…" : "Convert & Download"}
          </button>
        </div>
      )}

      {error && <p className="mt-4 text-sm text-red-600">{error}</p>}
    </div>
  );
}

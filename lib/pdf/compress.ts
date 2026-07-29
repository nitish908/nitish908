import { PDFDocument } from "pdf-lib";
import { loadPdfjs } from "@/lib/pdfjs";

export type CompressQuality = "low" | "medium" | "high";

const QUALITY_SETTINGS: Record<CompressQuality, { scale: number; jpegQuality: number }> = {
  low: { scale: 0.75, jpegQuality: 0.45 },
  medium: { scale: 1.0, jpegQuality: 0.6 },
  high: { scale: 1.5, jpegQuality: 0.75 },
};

/**
 * Rasterizes every page to a JPEG and reassembles a new PDF from the images.
 * Trades vector/text fidelity for file size — best suited to scanned or
 * image-heavy PDFs, which is the dominant real-world use case for "compress".
 */
export async function compressPdf(
  file: File,
  quality: CompressQuality = "medium"
): Promise<Uint8Array> {
  const { scale, jpegQuality } = QUALITY_SETTINGS[quality];
  const bytes = await file.arrayBuffer();

  const pdfjsLib = await loadPdfjs();
  const loadingTask = pdfjsLib.getDocument({ data: bytes });
  const pdf = await loadingTask.promise;
  const out = await PDFDocument.create();

  for (let pageNum = 1; pageNum <= pdf.numPages; pageNum++) {
    const page = await pdf.getPage(pageNum);
    const viewport = page.getViewport({ scale });

    const canvas = document.createElement("canvas");
    canvas.width = Math.ceil(viewport.width);
    canvas.height = Math.ceil(viewport.height);
    const ctx = canvas.getContext("2d");
    if (!ctx) throw new Error("Canvas not supported in this browser.");

    await page.render({ canvasContext: ctx, viewport }).promise;

    const jpegDataUrl = canvas.toDataURL("image/jpeg", jpegQuality);
    const jpegBytes = await (await fetch(jpegDataUrl)).arrayBuffer();
    const image = await out.embedJpg(jpegBytes);

    const outPage = out.addPage([viewport.width, viewport.height]);
    outPage.drawImage(image, {
      x: 0,
      y: 0,
      width: viewport.width,
      height: viewport.height,
    });
  }

  return out.save();
}

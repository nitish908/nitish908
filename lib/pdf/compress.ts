import { PDFDocument } from "pdf-lib";
import { loadPdfjs } from "@/lib/pdfjs";

export type CompressQuality = "low" | "medium" | "high";

const QUALITY_SETTINGS: Record<CompressQuality, { scale: number; jpegQuality: number }> = {
  low: { scale: 0.75, jpegQuality: 0.45 },
  medium: { scale: 1.0, jpegQuality: 0.6 },
  high: { scale: 1.5, jpegQuality: 0.75 },
};

// A page could declare an enormous MediaBox; without a cap, rasterizing it
// would try to allocate a canvas large enough to hang or crash the tab.
const MAX_CANVAS_DIMENSION = 8000;
const MAX_CANVAS_PIXELS = 40_000_000;

function canvasToBlob(canvas: HTMLCanvasElement, quality: number): Promise<Blob> {
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => (blob ? resolve(blob) : reject(new Error("Failed to encode page as JPEG."))),
      "image/jpeg",
      quality
    );
  });
}

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
    const width = Math.ceil(viewport.width);
    const height = Math.ceil(viewport.height);

    if (width > MAX_CANVAS_DIMENSION || height > MAX_CANVAS_DIMENSION || width * height > MAX_CANVAS_PIXELS) {
      throw new Error(
        `Page ${pageNum} is too large to compress in-browser (${width}×${height}px). Try a lower quality setting or a smaller source file.`
      );
    }

    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext("2d");
    if (!ctx) throw new Error("Canvas not supported in this browser.");

    await page.render({ canvasContext: ctx, viewport }).promise;

    const jpegBlob = await canvasToBlob(canvas, jpegQuality);
    const jpegBytes = await jpegBlob.arrayBuffer();
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

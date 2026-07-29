import { loadPdfjs } from "@/lib/pdfjs";

export type PageImage = { name: string; bytes: Uint8Array };

// See lib/pdf/compress.ts for why these caps exist: an attacker- or
// corruption-controlled MediaBox could otherwise try to allocate a
// canvas large enough to hang or crash the tab.
const MAX_CANVAS_DIMENSION = 8000;
const MAX_CANVAS_PIXELS = 40_000_000;

function canvasToBlob(canvas: HTMLCanvasElement, mime: string, quality?: number): Promise<Blob> {
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => (blob ? resolve(blob) : reject(new Error("Failed to encode page as an image."))),
      mime,
      quality
    );
  });
}

export async function pdfToImages(
  file: File,
  { scale = 2, format = "jpeg" as "jpeg" | "png", quality = 0.85 } = {}
): Promise<PageImage[]> {
  const bytes = await file.arrayBuffer();
  const pdfjsLib = await loadPdfjs();
  const pdf = await pdfjsLib.getDocument({ data: bytes }).promise;
  const results: PageImage[] = [];
  const mime = format === "png" ? "image/png" : "image/jpeg";
  const ext = format === "png" ? "png" : "jpg";

  for (let pageNum = 1; pageNum <= pdf.numPages; pageNum++) {
    const page = await pdf.getPage(pageNum);
    const viewport = page.getViewport({ scale });
    const width = Math.ceil(viewport.width);
    const height = Math.ceil(viewport.height);

    if (width > MAX_CANVAS_DIMENSION || height > MAX_CANVAS_DIMENSION || width * height > MAX_CANVAS_PIXELS) {
      throw new Error(
        `Page ${pageNum} is too large to export in-browser (${width}×${height}px). Try a smaller source file.`
      );
    }

    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext("2d");
    if (!ctx) throw new Error("Canvas not supported in this browser.");

    await page.render({ canvasContext: ctx, viewport }).promise;
    const blob = await canvasToBlob(canvas, mime, format === "jpeg" ? quality : undefined);
    const arrayBuffer = await blob.arrayBuffer();
    results.push({ name: `page-${pageNum}.${ext}`, bytes: new Uint8Array(arrayBuffer) });
  }

  return results;
}

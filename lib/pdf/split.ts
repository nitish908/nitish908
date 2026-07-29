import { PDFDocument } from "pdf-lib";

export type SplitResult = { name: string; bytes: Uint8Array };

/** Parses a page range string like "1-3,5,8-10" into zero-based page indices. */
export function parsePageRange(input: string, pageCount: number): number[] {
  const indices = new Set<number>();
  const parts = input.split(",").map((p) => p.trim()).filter(Boolean);

  for (const part of parts) {
    const rangeMatch = part.match(/^(\d+)\s*-\s*(\d+)$/);
    if (rangeMatch) {
      const start = Math.max(1, parseInt(rangeMatch[1], 10));
      const end = Math.min(pageCount, parseInt(rangeMatch[2], 10));
      for (let i = start; i <= end; i++) indices.add(i - 1);
    } else if (/^\d+$/.test(part)) {
      const page = parseInt(part, 10);
      if (page >= 1 && page <= pageCount) indices.add(page - 1);
    }
  }

  return Array.from(indices).sort((a, b) => a - b);
}

export async function extractPageRange(
  file: File,
  rangeInput: string
): Promise<SplitResult> {
  const bytes = await file.arrayBuffer();
  const src = await PDFDocument.load(bytes);
  const indices = parsePageRange(rangeInput, src.getPageCount());
  if (indices.length === 0) {
    throw new Error("No valid pages selected for the given range.");
  }

  const out = await PDFDocument.create();
  const pages = await out.copyPages(src, indices);
  pages.forEach((page) => out.addPage(page));

  return { name: "extracted.pdf", bytes: await out.save() };
}

export async function splitIntoPages(file: File): Promise<SplitResult[]> {
  const bytes = await file.arrayBuffer();
  const src = await PDFDocument.load(bytes);
  const count = src.getPageCount();
  const results: SplitResult[] = [];

  for (let i = 0; i < count; i++) {
    const out = await PDFDocument.create();
    const [page] = await out.copyPages(src, [i]);
    out.addPage(page);
    results.push({ name: `page-${i + 1}.pdf`, bytes: await out.save() });
  }

  return results;
}

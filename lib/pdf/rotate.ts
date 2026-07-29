import { PDFDocument, degrees } from "pdf-lib";

export async function rotatePdf(file: File, degreesToRotate: 90 | 180 | 270): Promise<Uint8Array> {
  const bytes = await file.arrayBuffer();
  const doc = await PDFDocument.load(bytes);

  for (const page of doc.getPages()) {
    const current = page.getRotation().angle;
    page.setRotation(degrees((current + degreesToRotate) % 360));
  }

  return doc.save();
}

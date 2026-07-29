# QuickPDF

Free, private, browser-based PDF tools — merge, split, watermark, and
compress PDFs without ever uploading a file to a server. Everything runs
client-side via `pdf-lib` and `pdfjs-dist`.

## Tools

- **Merge** (`/merge`) — combine multiple PDFs, reorder before merging.
- **Split** (`/split`) — extract a page range, or split into individual pages.
- **Watermark** (`/watermark`) — stamp diagonal text across every page.
- **Compress** (`/compress`) — shrink file size by rasterizing pages at a
  chosen quality; best for scanned/image-heavy PDFs.

## Development

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Notes

- `public/pdf.worker.min.mjs` is the `pdfjs-dist` worker, committed so the
  app is self-hosted with no CDN dependency. If `pdfjs-dist` is upgraded,
  regenerate it from `node_modules/pdfjs-dist/build/pdf.worker.min.mjs`.
- No backend, no database, no auth in this version — monetization
  (Stripe) is intentionally deferred until there's usage signal.

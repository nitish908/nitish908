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

- The `pdfjs-dist` worker (used by the Compress tool) is loaded from a CDN
  (jsdelivr) pinned to the installed `pdfjs-dist` version, keeping the repo
  free of a large committed binary. It only fetches the library — no PDF
  content is ever sent anywhere.
- No backend, no database, no auth in this version — monetization
  (Stripe) is intentionally deferred until there's usage signal.

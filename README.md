# QuickPDF

Free, private, browser-based PDF tools — nothing is ever uploaded to a
server. Everything runs client-side via `pdf-lib` and `pdfjs-dist`.

## Tools

- **Merge** (`/merge`) — combine multiple PDFs, reorder before merging.
- **Split** (`/split`) — extract a page range, or split into individual pages.
- **Rotate** (`/rotate`) — rotate every page by 90, 180, or 270 degrees.
- **Watermark** (`/watermark`) — stamp diagonal text across every page.
- **Compress** (`/compress`) — shrink file size by rasterizing pages at a
  chosen quality; best for scanned/image-heavy PDFs.
- **PDF to JPG** (`/pdf-to-jpg`) — export every page as a JPG image.
- **Images to PDF** (`/images-to-pdf`) — combine JPG/PNG images into a PDF.

## Development

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Security notes

- `public/pdf.worker.min.mjs` is the `pdfjs-dist` worker, self-hosted (no
  CDN) so the app makes zero third-party network requests — matching the
  "nothing ever leaves your browser" claim and avoiding a supply-chain
  dependency on a CDN. If `pdfjs-dist` is upgraded, regenerate it from
  `node_modules/pdfjs-dist/build/pdf.worker.min.mjs`.
- A Content-Security-Policy plus `X-Frame-Options`, `X-Content-Type-Options`,
  `Referrer-Policy`, and `Permissions-Policy` are set in `next.config.ts`.
  `connect-src 'self'` means the app cannot make any third-party network
  request even if a bug tried to. CSP intentionally does not use a nonce:
  nonce-based CSP requires every page to render dynamically per request,
  which would throw away static generation for an app with no backend and
  no per-user state — see the tradeoff explained in `next.config.ts`.
- The Compress and PDF-to-JPG tools cap rasterization dimensions
  (`lib/pdf/compress.ts`, `lib/pdf/toImages.ts`) so a PDF with a malicious
  or corrupted oversized page can't hang or crash the tab.
- `FileDropzone` enforces a max file size (150MB default) client-side for
  the same reason — very large files could otherwise freeze the tab before
  any processing logic even runs.
- No backend, no database, no auth in this version — monetization
  (Stripe) is intentionally deferred until there's usage signal.

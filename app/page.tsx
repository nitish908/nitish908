import Link from "next/link";

const TOOLS = [
  {
    href: "/merge",
    title: "Merge PDF",
    description: "Combine multiple PDFs into one file, in any order you choose.",
  },
  {
    href: "/split",
    title: "Split PDF",
    description: "Pull out a page range, or break a PDF into individual pages.",
  },
  {
    href: "/watermark",
    title: "Watermark PDF",
    description: "Stamp text like \"DRAFT\" or your name across every page.",
  },
  {
    href: "/compress",
    title: "Compress PDF",
    description: "Shrink file size — great for scanned or image-heavy PDFs.",
  },
];

export default function Home() {
  return (
    <div className="mx-auto max-w-5xl px-6 py-20">
      <div className="text-center">
        <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
          PDF tools that never see your files
        </h1>
        <p className="mx-auto mt-4 max-w-2xl text-lg text-zinc-600 dark:text-zinc-400">
          Merge, split, watermark, and compress PDFs entirely in your browser.
          Nothing is uploaded to a server — your documents never leave your
          device. Free, no sign-up.
        </p>
      </div>

      <div className="mt-14 grid gap-6 sm:grid-cols-2">
        {TOOLS.map((tool) => (
          <Link
            key={tool.href}
            href={tool.href}
            className="rounded-xl border border-zinc-200 p-6 transition-colors hover:border-blue-400 hover:bg-blue-50/50 dark:border-zinc-800 dark:hover:border-blue-700 dark:hover:bg-blue-950/20"
          >
            <h2 className="text-lg font-semibold">{tool.title}</h2>
            <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-400">
              {tool.description}
            </p>
          </Link>
        ))}
      </div>

      <div className="mt-16 grid gap-8 text-sm text-zinc-600 dark:text-zinc-400 sm:grid-cols-3">
        <div>
          <h3 className="font-semibold text-zinc-900 dark:text-zinc-100">100% private</h3>
          <p className="mt-1">All processing happens locally in your browser via JavaScript.</p>
        </div>
        <div>
          <h3 className="font-semibold text-zinc-900 dark:text-zinc-100">No sign-up</h3>
          <p className="mt-1">Just drop a file and go. No account, no email required.</p>
        </div>
        <div>
          <h3 className="font-semibold text-zinc-900 dark:text-zinc-100">Free</h3>
          <p className="mt-1">Every tool on this site is free to use, with no limits.</p>
        </div>
      </div>
    </div>
  );
}

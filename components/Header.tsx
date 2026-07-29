import Link from "next/link";

const TOOLS = [
  { href: "/merge", label: "Merge" },
  { href: "/split", label: "Split" },
  { href: "/rotate", label: "Rotate" },
  { href: "/watermark", label: "Watermark" },
  { href: "/compress", label: "Compress" },
  { href: "/pdf-to-jpg", label: "PDF to JPG" },
  { href: "/images-to-pdf", label: "Images to PDF" },
];

export default function Header() {
  return (
    <header className="border-b border-zinc-200 dark:border-zinc-800">
      <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-x-6 gap-y-2 px-6 py-4">
        <Link href="/" className="text-lg font-semibold tracking-tight">
          Quick<span className="text-blue-600">PDF</span>
        </Link>
        <nav className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm font-medium text-zinc-600 dark:text-zinc-400">
          {TOOLS.map((t) => (
            <Link key={t.href} href={t.href} className="hover:text-zinc-950 dark:hover:text-zinc-50">
              {t.label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}

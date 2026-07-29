import Link from "next/link";

const TOOLS = [
  { href: "/merge", label: "Merge" },
  { href: "/split", label: "Split" },
  { href: "/watermark", label: "Watermark" },
  { href: "/compress", label: "Compress" },
];

export default function Header() {
  return (
    <header className="border-b border-zinc-200 dark:border-zinc-800">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
        <Link href="/" className="text-lg font-semibold tracking-tight">
          Quick<span className="text-blue-600">PDF</span>
        </Link>
        <nav className="flex items-center gap-5 text-sm font-medium text-zinc-600 dark:text-zinc-400">
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

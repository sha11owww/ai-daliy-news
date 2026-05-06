interface HeaderProps {
  title: string;
  date: string;
}

export default function Header({ title, date }: HeaderProps) {
  return (
    <header className="border-b border-border bg-card">
      <div className="max-w-3xl mx-auto px-4 py-4 flex items-center justify-between">
        <a href="/" className="text-xl font-bold text-ink-dark no-underline">
          📰 {title}
        </a>
        <time className="text-sm text-ink-light">{date}</time>
      </div>
    </header>
  );
}

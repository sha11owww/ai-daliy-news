interface Section {
  name: string;
}

interface FilterBarProps {
  sections: Section[];
  activeSection: string | null;
  onSelect: (section: string | null) => void;
}

export default function FilterBar({ sections, activeSection, onSelect }: FilterBarProps) {
  return (
    <div className="flex gap-2 overflow-x-auto pb-2">
      <button
        onClick={() => onSelect(null)}
        className={`px-3 py-1.5 rounded-full text-sm whitespace-nowrap transition-colors ${
          activeSection === null
            ? 'bg-card text-ink-dark font-medium'
            : 'bg-transparent text-ink-light border border-border hover:bg-card'
        }`}
      >
        🔄 全部
      </button>
      {sections.map((s) => (
        <button
          key={s.name}
          onClick={() => onSelect(s.name)}
          className={`px-3 py-1.5 rounded-full text-sm whitespace-nowrap transition-colors ${
            activeSection === s.name
              ? 'bg-card text-ink-dark font-medium'
              : 'bg-transparent text-ink-light border border-border hover:bg-card'
          }`}
        >
          {s.name}
        </button>
      ))}
    </div>
  );
}

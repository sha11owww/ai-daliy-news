import type { Article } from '../api';

interface CardProps {
  article: Article;
  isHeadline?: boolean;
}

export default function Card({ article, isHeadline }: CardProps) {
  const detailUrl = article.id && article.id > 0
    ? `/article/${article.id}`
    : `/article?date=${article.published_date || ''}&url=${encodeURIComponent(article.url)}`;

  return (
    <a
      href={detailUrl}
      className={`block no-underline rounded-xl border ${
        isHeadline
          ? 'bg-card border-border card-hover'
          : 'bg-white border-card card-hover'
      }`}
    >
      <div className="p-4">
        {isHeadline && (
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xs font-medium text-ink bg-paper px-2 py-0.5 rounded-full">
              🔥 头条
            </span>
            <span className="text-xs text-ink-light">{article.source}</span>
          </div>
        )}

        <h3
          className={`font-bold text-ink-dark leading-snug mb-1 ${
            isHeadline ? 'text-lg' : 'text-base'
          }`}
        >
          {article.title}
        </h3>

        <p className="text-sm text-ink leading-relaxed line-clamp-2">
          {isHeadline ? article.summary : article.brief || article.summary}
        </p>

        <div className="flex items-center gap-2 mt-3 flex-wrap">
          {article.tags.slice(0, 3).map((tag) => (
            <span
              key={tag}
              className="text-xs px-2 py-0.5 rounded-full bg-card text-ink border border-border"
            >
              {tag}
            </span>
          ))}
          {!isHeadline && (
            <span className="text-xs text-ink-light ml-auto">{article.source}</span>
          )}
        </div>
      </div>
    </a>
  );
}

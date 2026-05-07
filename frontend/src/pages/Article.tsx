import { useEffect, useState } from 'react';
import { useParams, useSearchParams, Link } from 'react-router-dom';
import type { Article as ArticleType } from '../api';
import { fetchArticle } from '../api';

const API_BASE = '/api';

export default function Article() {
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const [article, setArticle] = useState<ArticleType | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      // 方式1：通过数据库 ID 加载
      if (id) {
        const data = await fetchArticle(Number(id));
        if (data) { setArticle(data); setLoading(false); return; }
      }

      // 方式2：通过日期+URL 从 JSON 查找
      const date = searchParams.get('date');
      const url = searchParams.get('url');
      if (date && url) {
        try {
          const res = await fetch(`${API_BASE}/reports/${date}`);
          const reports = await res.json();
          if (Array.isArray(reports)) {
            for (const r of reports) {
              for (const a of (r.articles || [])) {
                if (a.url === url) { setArticle(a); break; }
              }
            }
          }
        } catch {}
      }
      setLoading(false);
    }
    load();
  }, [id, searchParams]);

  if (loading) {
    return (
      <div className="min-h-screen bg-paper flex items-center justify-center">
        <p className="text-ink-light">加载中...</p>
      </div>
    );
  }

  if (!article) {
    return (
      <div className="min-h-screen bg-paper flex items-center justify-center">
        <p className="text-ink-light">文章不存在</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-paper">
      <main className="max-w-2xl mx-auto px-4 py-8">
        <Link to="/" className="text-sm text-ink-light hover:text-ink mb-6 inline-block">
          ← 返回日报
        </Link>

        {article.tags.length > 0 && (
          <span className="inline-block text-xs text-ink-light bg-card px-2 py-0.5 rounded-full mb-3">
            {article.tags[0]}
          </span>
        )}

        <h1 className="text-2xl font-bold text-ink-dark leading-snug mb-4">
          {article.title}
        </h1>

        <div className="flex items-center gap-4 text-sm text-ink-light mb-8">
          <time>{article.published_date}</time>
          <span>📰 {article.source}</span>
          <a
            href={article.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-ink underline hover:text-ink-dark ml-auto"
          >
            🔗 查看原文
          </a>
        </div>

        {article.summary && (
          <div className="text-base text-ink leading-relaxed mb-8 whitespace-pre-line">
            {article.summary}
          </div>
        )}

        {article.tags.length > 0 && (
          <div className="mt-8 pt-6 border-t border-border flex gap-2 flex-wrap">
            {article.tags.map((tag) => (
              <span
                key={tag}
                className="text-sm px-3 py-1 bg-card rounded-full text-ink"
              >
                {tag}
              </span>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}

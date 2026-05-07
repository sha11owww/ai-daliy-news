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
      const urlParam = searchParams.get('url');

      // 方式1：通过数据库 ID 加载
      if (id && !urlParam) {
        const data = await fetchArticle(Number(id));
        if (data) { setArticle(data); setLoading(false); return; }
      }

      // 方式2：通过 URL 从当天及历史日报 JSON 中查找
      if (urlParam) {
        try {
          const res = await fetch(`${API_BASE}/reports/`);
          const reports = await res.json();
          // 遍历近 7 天日报
          for (const r of reports.slice(0, 14)) {
            const detailRes = await fetch(`${API_BASE}/reports/${r.report_date}`);
            const dayReports = await detailRes.json();
            const list = Array.isArray(dayReports) ? dayReports : [dayReports];
            for (const day of list) {
              for (const a of (day.articles || [])) {
                if (a.url === urlParam) { setArticle(a); setLoading(false); return; }
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

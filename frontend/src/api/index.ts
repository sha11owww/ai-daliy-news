const API_BASE = '/api';

export interface Article {
  id: number;
  title: string;
  url: string;
  source: string;
  summary: string | null;
  brief: string | null;
  tags: string[];
  section: string | null;
  importance_score: number;
  published_date: string;
  metadata: Record<string, unknown>;
}

export interface DailyReport {
  id: number;
  report_date: string;
  title: string;
  article_order: number[];
  sections: Array<{ name: string; article_ids: number[] }>;
  editor_notes: string | null;
  total_articles: number;
  status: string;
  articles: Article[];
}

export interface ReportSummary {
  id: number;
  report_date: string;
  title: string;
  total_articles: number;
  status: string;
}

export async function fetchTodayReport(): Promise<DailyReport | null> {
  const res = await fetch(`${API_BASE}/reports/today`);
  if (!res.ok) return null;
  return res.json();
}

export async function fetchArticle(id: number): Promise<Article | null> {
  const res = await fetch(`${API_BASE}/articles/${id}`);
  if (!res.ok) return null;
  return res.json();
}

export async function fetchReports(limit = 30): Promise<ReportSummary[]> {
  const res = await fetch(`${API_BASE}/reports/?limit=${limit}`);
  return res.json();
}

export async function fetchArticles(params?: {
  report_date?: string;
  source?: string;
  section?: string;
}): Promise<Article[]> {
  const query = new URLSearchParams();
  if (params?.report_date) query.set('report_date', params.report_date);
  if (params?.source) query.set('source', params.source);
  if (params?.section) query.set('section', params.section);
  const res = await fetch(`${API_BASE}/articles/?${query}`);
  return res.json();
}

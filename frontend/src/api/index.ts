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
  session_type: string;
  title: string;
  article_order: number[];
  sections: Array<{ name: string; article_ids: number[] }>;
  editor_notes: string | null;
  total_articles: number;
  status: string;
  articles: Article[];
}

export interface DailyReportMap {
  morning: DailyReport | null;
  evening: DailyReport | null;
}

export interface CalendarEntry {
  date: string;
  sessions: string[];
}

export interface ReportSummary {
  id: number;
  report_date: string;
  session_type: string;
  title: string;
  total_articles: number;
  status: string;
}

/** 获取今日完整日报（含早报+晚报） */
export async function fetchTodayReport(): Promise<DailyReportMap | null> {
  const res = await fetch(`${API_BASE}/reports/today`);
  if (!res.ok) return null;
  return res.json();
}

/** 获取今日指定时段日报 */
export async function fetchTodaySessionReport(session: 'morning' | 'evening'): Promise<DailyReport | null> {
  const res = await fetch(`${API_BASE}/reports/today/${session}`);
  if (!res.ok) return null;
  return res.json();
}

/** 获取单篇文章详情 */
export async function fetchArticle(id: number): Promise<Article | null> {
  const res = await fetch(`${API_BASE}/articles/${id}`);
  if (!res.ok) return null;
  return res.json();
}

/** 获取历史日报列表 */
export async function fetchReports(limit = 30): Promise<ReportSummary[]> {
  const res = await fetch(`${API_BASE}/reports/?limit=${limit}`);
  return res.json();
}

/** 获取文章列表（支持筛选） */
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

/** 获取日历数据 */
export async function fetchCalendar(year?: number, month?: number): Promise<CalendarEntry[]> {
  const query = new URLSearchParams();
  if (year) query.set('year', String(year));
  if (month) query.set('month', String(month));
  const res = await fetch(`${API_BASE}/reports/calendar?${query}`);
  return res.json();
}

/** 按日期和时段获取历史日报 */
export async function fetchReportByDateAndSession(date: string, session: 'morning' | 'evening'): Promise<DailyReport | null> {
  const res = await fetch(`${API_BASE}/reports/${date}/${session}`);
  if (!res.ok) return null;
  return res.json();
}

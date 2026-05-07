import { useEffect, useState, useCallback, useRef } from 'react';
import type { DailyReport } from '../api';
import { fetchTodayReport } from '../api';
import Header from '../components/Header';
import FilterBar from '../components/FilterBar';
import Card from '../components/Card';
import Calendar from '../components/Calendar';

const API_BASE = '/api';
type SessionTab = 'morning' | 'evening';

export default function Home() {
  const [morningReport, setMorningReport] = useState<DailyReport | null>(null);
  const [eveningReport, setEveningReport] = useState<DailyReport | null>(null);
  const [activeSession, setActiveSession] = useState<SessionTab>('morning');
  const [loading, setLoading] = useState(true);
  const [activeSection, setActiveSection] = useState<string | null>(null);
  const [selectedCalendarDate, setSelectedCalendarDate] = useState<string | null>(null);
  const [prevReports, setPrevReports] = useState<{morning: DailyReport|null; evening: DailyReport|null}>({morning: null, evening: null});
  const fetchingRef = useRef<string | null>(null);

  useEffect(() => {
    fetchTodayReport().then((data) => {
      if (data) {
        setMorningReport(data.morning);
        setEveningReport(data.evening);
      }
      setLoading(false);
    });
  }, []);

  const handleCalendarSelect = useCallback(async (dateStr: string) => {
    if (dateStr === selectedCalendarDate) return;

    setPrevReports({morning: morningReport, evening: eveningReport});
    setSelectedCalendarDate(dateStr);
    setActiveSection(null);

    // 标记当前请求，忽略过期响应
    fetchingRef.current = dateStr;
    try {
      const res = await fetch(`${API_BASE}/reports/${dateStr}`);
      if (fetchingRef.current !== dateStr) return; // 已被新请求替代
      if (!res.ok) { setMorningReport(null); setEveningReport(null); return; }
      const reports: DailyReport[] = await res.json();
      if (fetchingRef.current !== dateStr) return;
      setMorningReport(reports.find((r) => r.session_type === 'morning') || null);
      setEveningReport(reports.find((r) => r.session_type === 'evening') || null);
    } catch {
      if (fetchingRef.current === dateStr) {
        setMorningReport(null); setEveningReport(null);
      }
    }
  }, [selectedCalendarDate, morningReport, eveningReport]);

  const handleBackToToday = () => {
    setSelectedCalendarDate(null);
    setMorningReport(prevReports.morning);
    setEveningReport(prevReports.evening);
  };

  const report = activeSession === 'morning' ? morningReport : eveningReport;

  if (loading) {
    return (
      <div className="min-h-screen bg-paper flex items-center justify-center">
        <p className="text-ink-light">加载中...</p>
      </div>
    );
  }

  const displayDate = selectedCalendarDate || '';
  const reportTitle = report?.title || 'AI Daily';

  const sessionTabs = (
    <div className="pt-4 pb-2">
      <div className="flex items-center gap-3 text-sm">
        <button onClick={() => { setActiveSession('morning'); setActiveSection(null); }}
          className={`transition-colors ${activeSession === 'morning' ? 'text-ink-dark font-medium' : 'text-ink-light hover:text-ink-dark'}`}>
          ☀️ 早报
        </button>
        <span className="text-border">·</span>
        <button onClick={() => { setActiveSession('evening'); setActiveSection(null); }}
          className={`transition-colors ${activeSession === 'evening' ? 'text-ink-dark font-medium' : 'text-ink-light hover:text-ink-dark'}`}>
          🌙 晚报
        </button>
        <span className="ml-auto text-xs text-ink-light">
          {selectedCalendarDate && <button onClick={handleBackToToday} className="underline">← 返回今天</button>}
          {!selectedCalendarDate && activeSession === 'morning' && (morningReport ? '✅ 已出' : '⏳ 待发布')}
          {!selectedCalendarDate && activeSession === 'evening' && (eveningReport ? '✅ 已出' : '⏳ 待发布')}
        </span>
      </div>
      <div className="mt-2 h-px bg-border" />
    </div>
  );

  const renderContent = () => {
    if (!report) {
      return <p className="text-ink-light text-lg text-center py-12">{activeSession === 'morning' ? '早报' : '晚报'}暂无内容</p>;
    }
    const sections = report.sections || [];
    const headlines = report.articles?.filter((a: any) => a.importance_score >= 4) || [];
    const others = report.articles?.filter((a: any) => a.importance_score < 4) || [];
    const filteredOthers = activeSection ? others.filter((a: any) => a.section === activeSection) : others;
    return (
      <>
        {sections.length > 0 && (
          <div className="mb-6">
            <FilterBar sections={sections as { name: string }[]} activeSection={activeSection} onSelect={setActiveSection} />
          </div>
        )}
        {headlines.length > 0 && !activeSection && (
          <section className="mb-8"><div className="flex flex-col gap-4">
            {headlines.map((article: any) => (<Card key={article.id} article={article} isHeadline />))}
          </div></section>
        )}
        <section>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {(activeSection ? filteredOthers : others).map((article: any) => (<Card key={article.id} article={article} />))}
          </div>
        </section>
        <footer className="mt-8 pt-4 border-t border-border text-center text-xs text-ink-light">本日共 {report.total_articles} 篇 · 由 AI 自动整理</footer>
      </>
    );
  };

  return (
    <div className="min-h-screen bg-paper">
      <Header title={reportTitle} date={displayDate} />
      <main className="max-w-5xl mx-auto px-4 py-6 flex gap-6">
        <div className="hidden lg:block w-72 flex-shrink-0">
          <Calendar selectedDate={selectedCalendarDate} onSelectDate={handleCalendarSelect} compact />
        </div>
        <div className="flex-1 min-w-0">
          {sessionTabs}
          {renderContent()}
        </div>
      </main>
    </div>
  );
}

import { useEffect, useState, useCallback } from 'react';
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

  // 初始加载：今日日报
  useEffect(() => {
    fetchTodayReport().then((data) => {
      if (data) {
        setMorningReport(data.morning);
        setEveningReport(data.evening);
      }
      setLoading(false);
    });
  }, []);

  // 日历选择日期
  const handleCalendarSelect = useCallback(async (dateStr: string) => {
    if (dateStr === selectedCalendarDate) return;
    setSelectedCalendarDate(dateStr);
    setActiveSection(null);
    setMorningReport(null);
    setEveningReport(null);

    try {
      const res = await fetch(`${API_BASE}/reports/${dateStr}`);
      if (!res.ok) return;
      const reports: DailyReport[] = await res.json();
      setMorningReport(reports.find((r) => r.session_type === 'morning') || null);
      setEveningReport(reports.find((r) => r.session_type === 'evening') || null);
    } catch {
      // 请求失败时保持空状态
    }
  }, [selectedCalendarDate]);

  const report = activeSession === 'morning' ? morningReport : eveningReport;

  if (loading) {
    return (
      <div className="min-h-screen bg-paper flex items-center justify-center">
        <p className="text-ink-light">加载中...</p>
      </div>
    );
  }

  const displayDate = selectedCalendarDate || new Date().toLocaleDateString('zh-CN');
  const reportTitle = report?.title || (selectedCalendarDate ? `${selectedCalendarDate} AI 日报` : 'AI Daily');

  const sessionTabs = (
    <div className="pt-4 pb-2">
      <div className="flex items-center gap-3 text-sm">
        <button
          onClick={() => { setActiveSession('morning'); setActiveSection(null); }}
          className={`transition-colors ${
            activeSession === 'morning' ? 'text-ink-dark font-medium' : 'text-ink-light hover:text-ink-dark'
          }`}
        >
          ☀️ 早报
        </button>
        <span className="text-border">·</span>
        <button
          onClick={() => { setActiveSession('evening'); setActiveSection(null); }}
          className={`transition-colors ${
            activeSession === 'evening' ? 'text-ink-dark font-medium' : 'text-ink-light hover:text-ink-dark'
          }`}
        >
          🌙 晚报
        </button>
        {/* 显示已出状态 */}
        <span className="ml-auto text-xs text-ink-light">
          {activeSession === 'morning' && morningReport ? '✅ 已出' : ''}
          {activeSession === 'evening' && eveningReport ? '✅ 已出' : ''}
          {activeSession === 'morning' && !morningReport ? '⏳ 待发布' : ''}
          {activeSession === 'evening' && !eveningReport ? '⏳ 待发布' : ''}
        </span>
      </div>
      {/* 时间线装饰线 */}
      <div className="mt-2 h-px bg-border" />
    </div>
  );

  // 渲染日报内容（或空状态）
  const renderContent = () => {
    if (!report) {
      return (
        <p className="text-ink-light text-lg text-center py-12">
          {activeSession === 'morning' ? '早报' : '晚报'}暂无内容
        </p>
      );
    }

    const sections = report.sections || [];
    const headlines = report.articles?.filter((a) => a.importance_score >= 4) || [];
    const others = report.articles?.filter((a) => a.importance_score < 4) || [];
    const filteredOthers = activeSection
      ? others.filter((a) => a.section === activeSection)
      : others;

    return (
      <>
        {sections.length > 0 && (
          <div className="mb-6">
            <FilterBar
              sections={sections as { name: string }[]}
              activeSection={activeSection}
              onSelect={setActiveSection}
            />
          </div>
        )}

        {headlines.length > 0 && !activeSection && (
          <section className="mb-8">
            <div className="flex flex-col gap-4">
              {headlines.map((article) => (
                <Card key={article.id} article={article} isHeadline />
              ))}
            </div>
          </section>
        )}

        <section>
          {sections.length > 0 && !activeSection && (
            <div className="flex gap-2 mb-4 text-xs text-ink-light">
              {sections.map((s: { name: string }) => (
                <span key={s.name} className="bg-card px-2 py-0.5 rounded">
                  📂 {s.name}
                </span>
              ))}
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {(activeSection ? filteredOthers : others).map((article) => (
              <Card key={article.id} article={article} />
            ))}
          </div>
        </section>

        <footer className="mt-8 pt-4 border-t border-border text-center text-xs text-ink-light">
          本日共 {report.total_articles} 篇 · 由 AI 自动整理
        </footer>
      </>
    );
  };

  return (
    <div className="min-h-screen bg-paper">
      <Header title={reportTitle} date={displayDate} />

      <main className="max-w-5xl mx-auto px-4 py-6 flex gap-6">
        {/* 左侧日历（桌面端显示） */}
        <div className="hidden lg:block w-72 flex-shrink-0">
          <Calendar
            selectedDate={selectedCalendarDate}
            onSelectDate={handleCalendarSelect}
            compact
          />
        </div>

        {/* 右侧日报内容 */}
        <div className="flex-1 min-w-0">
          {sessionTabs}
          {renderContent()}
        </div>
      </main>
    </div>
  );
}

import { useEffect, useState } from 'react';
import type { DailyReport } from '../api';
import { fetchTodayReport } from '../api';
import Header from '../components/Header';
import FilterBar from '../components/FilterBar';
import Card from '../components/Card';

type SessionTab = 'morning' | 'evening';

export default function Home() {
  const [morningReport, setMorningReport] = useState<DailyReport | null>(null);
  const [eveningReport, setEveningReport] = useState<DailyReport | null>(null);
  const [activeSession, setActiveSession] = useState<SessionTab>('morning');
  const [loading, setLoading] = useState(true);
  const [activeSection, setActiveSection] = useState<string | null>(null);

  useEffect(() => {
    fetchTodayReport().then((data) => {
      if (data) {
        setMorningReport(data.morning);
        setEveningReport(data.evening);
      }
      setLoading(false);
    });
  }, []);

  const report = activeSession === 'morning' ? morningReport : eveningReport;

  if (loading) {
    return (
      <div className="min-h-screen bg-paper flex items-center justify-center">
        <p className="text-ink-light">加载中...</p>
      </div>
    );
  }

  const sessionTabs = (
    <div className="max-w-3xl mx-auto px-4 pt-4 pb-2">
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

  if (!report) {
    const today = new Date().toLocaleDateString('zh-CN');
    return (
      <div className="min-h-screen bg-paper">
        <Header title="AI Daily" date={today} />
        <main className="max-w-3xl mx-auto px-4 py-8">
          {sessionTabs}
          <p className="text-ink-light text-lg text-center py-12">
            今日{activeSession === 'morning' ? '早报' : '晚报'}正在编辑中，请稍后再来 📝
          </p>
        </main>
      </div>
    );
  }

  const sections = report.sections || [];
  const headlines = report.articles?.filter((a) => a.importance_score >= 4) || [];
  const others = report.articles?.filter((a) => a.importance_score < 4) || [];
  const filteredOthers = activeSection
    ? others.filter((a) => a.section === activeSection)
    : others;

  return (
    <div className="min-h-screen bg-paper">
      <Header title={report.title} date={report.report_date} />

      <main className="max-w-3xl mx-auto px-4 py-6">
        {sessionTabs}

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
      </main>
    </div>
  );
}

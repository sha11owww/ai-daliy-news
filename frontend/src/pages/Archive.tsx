import { useEffect, useState, useCallback } from 'react';
import type { CalendarEntry, DailyReport } from '../api';
import { fetchCalendar, fetchReportByDateAndSession } from '../api';
import Header from '../components/Header';
import Card from '../components/Card';

const WEEK_DAYS = ['日', '一', '二', '三', '四', '五', '六'];
const MONTH_NAMES = ['一月', '二月', '三月', '四月', '五月', '六月', '七月', '八月', '九月', '十月', '十一月', '十二月'];

/** 纯日历组件 - 日期数据计算 + 网格布局渲染 */
export default function Archive() {
  const today = new Date();
  const [viewYear, setViewYear] = useState(today.getFullYear());
  const [viewMonth, setViewMonth] = useState(today.getMonth() + 1);
  const [calendarData, setCalendarData] = useState<CalendarEntry[]>([]);
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [detailReports, setDetailReports] = useState<{
    morning: DailyReport | null;
    evening: DailyReport | null;
  }>({ morning: null, evening: null });
  const [detailLoading, setDetailLoading] = useState(false);

  // 日期 -> 时段 映射表
  const dateMap = new Map<string, string[]>();
  calendarData.forEach((entry) => dateMap.set(entry.date, entry.sessions));

  useEffect(() => {
    fetchCalendar(viewYear, viewMonth).then(setCalendarData);
  }, [viewYear, viewMonth]);

  /** 点击日期加载该日所有日报 */
  const handleDateClick = useCallback(
    async (dateStr: string) => {
      setSelectedDate(dateStr);
      setDetailLoading(true);
      setDetailReports({ morning: null, evening: null });

      const sessions = dateMap.get(dateStr) || [];
      const results: { morning: DailyReport | null; evening: DailyReport | null } = {
        morning: null,
        evening: null,
      };

      for (const s of sessions) {
        const report = await fetchReportByDateAndSession(dateStr, s as 'morning' | 'evening');
        if (report) results[s as 'morning' | 'evening'] = report;
      }
      setDetailReports(results);
      setDetailLoading(false);
    },
    [dateMap],
  );

  const goPrevMonth = () => {
    if (viewMonth === 1) {
      setViewYear(viewYear - 1);
      setViewMonth(12);
    } else {
      setViewMonth(viewMonth - 1);
    }
    setSelectedDate(null);
    setDetailReports({ morning: null, evening: null });
  };

  const goNextMonth = () => {
    if (viewMonth === 12) {
      setViewYear(viewYear + 1);
      setViewMonth(1);
    } else {
      setViewMonth(viewMonth + 1);
    }
    setSelectedDate(null);
    setDetailReports({ morning: null, evening: null });
  };

  // 日历网格数据
  const firstDay = new Date(viewYear, viewMonth - 1, 1).getDay();
  const daysInMonth = new Date(viewYear, viewMonth, 0).getDate();
  const fmt = (d: number) =>
    `${viewYear}-${String(viewMonth).padStart(2, '0')}-${String(d).padStart(2, '0')}`;

  const cells: (number | null)[] = [];
  for (let i = 0; i < firstDay; i++) cells.push(null);
  for (let d = 1; d <= daysInMonth; d++) cells.push(d);

  return (
    <div className="min-h-screen bg-paper">
      <Header title="历史日报" date={`${viewYear}年 ${viewMonth}月`} />

      <main className="max-w-5xl mx-auto px-4 py-6 flex flex-col lg:flex-row gap-6">
        {/* ===== 日历卡片 ===== */}
        <div className="lg:w-[350px] flex-shrink-0 bg-white rounded-xl border border-border shadow-sm overflow-hidden">
          {/* 月份导航 */}
          <div className="flex items-center justify-between px-5 py-4 border-b border-border">
            <button
              onClick={goPrevMonth}
              className="text-sm text-ink-light hover:text-ink-dark transition-colors"
            >
              ← 上月
            </button>
            <h2 className="text-base font-bold text-ink-dark">
              {viewYear} 年 {MONTH_NAMES[viewMonth - 1]}
            </h2>
            <button
              onClick={goNextMonth}
              className="text-sm text-ink-light hover:text-ink-dark transition-colors"
            >
              下月 →
            </button>
          </div>

          {/* 星期表头 */}
          <div className="grid grid-cols-7 px-3 pt-4 pb-1">
            {WEEK_DAYS.map((wd) => (
              <div key={wd} className="text-center text-xs font-medium text-ink-light">
                {wd}
              </div>
            ))}
          </div>

          {/* 日期网格 */}
          <div className="grid grid-cols-7 px-3 pb-4 gap-y-1">
            {cells.map((day, idx) => {
              if (day === null) return <div key={`e-${idx}`} />;

              const dateStr = fmt(day);
              const sessions = dateMap.get(dateStr);
              const isSelected = selectedDate === dateStr;
              const isToday =
                fmt(today.getDate()) === dateStr &&
                viewYear === today.getFullYear() &&
                viewMonth === today.getMonth() + 1;

              return (
                <button
                  key={dateStr}
                  onClick={() => handleDateClick(dateStr)}
                  className="flex flex-col items-center py-1.5 rounded-lg transition-all duration-150 relative"
                >
                  {/* 今日高亮 */}
                  {isToday && !isSelected && (
                    <div className="absolute inset-0 rounded-lg bg-card border border-border" />
                  )}
                  {/* 选中高亮 */}
                  {isSelected && (
                    <div className="absolute inset-0 rounded-lg bg-ink-dark" />
                  )}

                  {/* 日期数字 */}
                  <span
                    className={`relative z-10 text-sm font-medium leading-tight ${
                      isSelected ? 'text-white' : isToday ? 'text-ink-dark' : 'text-ink-light'
                    }`}
                  >
                    {day}
                  </span>

                  {/* 日报标记 */}
                  {sessions && (
                    <div className="relative z-10 flex gap-1 mt-1">
                      {sessions.includes('morning') && (
                        <span
                          className={`text-[10px] px-1 rounded font-medium ${
                            isSelected
                              ? 'bg-yellow-300 text-ink-dark'
                              : 'bg-yellow-100 text-yellow-700'
                          }`}
                        >
                          早
                        </span>
                      )}
                      {sessions.includes('evening') && (
                        <span
                          className={`text-[10px] px-1 rounded font-medium ${
                            isSelected
                              ? 'bg-blue-300 text-white'
                              : 'bg-blue-100 text-blue-700'
                          }`}
                        >
                          晚
                        </span>
                      )}
                    </div>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* ===== 右侧日报详情 ===== */}
        <div className="flex-1 min-w-0">
          {!selectedDate && !detailLoading && (
            <div className="flex items-center justify-center h-80 text-ink-light">
              <div className="text-center">
                <p className="text-3xl mb-3">📅</p>
                <p className="text-base">选择左侧日历中的日期查看历史日报</p>
              </div>
            </div>
          )}

          {detailLoading && (
            <div className="flex items-center justify-center h-80 text-ink-light">
              <p>加载中...</p>
            </div>
          )}

          {(detailReports.morning || detailReports.evening) && !detailLoading && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {detailReports.morning && (
                <div>
                  <h3 className="text-base font-bold text-ink-dark mb-3 flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-yellow-500 inline-block" />
                    ☀️ 早报 · {detailReports.morning.total_articles} 篇
                  </h3>
                  <div className="flex flex-col gap-2">
                    {detailReports.morning.articles?.map((a) => (
                      <Card key={a.id} article={a} isHeadline={a.importance_score >= 4} />
                    ))}
                  </div>
                </div>
              )}
              {detailReports.evening && (
                <div>
                  <h3 className="text-base font-bold text-ink-dark mb-3 flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-blue-500 inline-block" />
                    🌙 晚报 · {detailReports.evening.total_articles} 篇
                  </h3>
                  <div className="flex flex-col gap-2">
                    {detailReports.evening.articles?.map((a) => (
                      <Card key={a.id} article={a} isHeadline={a.importance_score >= 4} />
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

import { useEffect, useState, useCallback } from 'react';
import type { CalendarEntry, DailyReport } from '../api';
import { fetchCalendar, fetchReportByDateAndSession } from '../api';
import Header from '../components/Header';
import Card from '../components/Card';

export default function Archive() {
  const today = new Date();
  const [viewYear, setViewYear] = useState(today.getFullYear());
  const [viewMonth, setViewMonth] = useState(today.getMonth() + 1);
  const [calendarData, setCalendarData] = useState<CalendarEntry[]>([]);
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [detailReports, setDetailReports] = useState<{ morning: DailyReport | null; evening: DailyReport | null }>({
    morning: null, evening: null,
  });
  const [detailLoading, setDetailLoading] = useState(false);

  const dateMap = new Map<string, string[]>();
  calendarData.forEach((entry) => dateMap.set(entry.date, entry.sessions));

  useEffect(() => {
    fetchCalendar(viewYear, viewMonth).then(setCalendarData);
  }, [viewYear, viewMonth]);

  const handleDateClick = useCallback(async (dateStr: string) => {
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
      if (report) {
        results[s as 'morning' | 'evening'] = report;
      }
    }
    setDetailReports(results);
    setDetailLoading(false);
  }, [dateMap]);

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

  const firstDay = new Date(viewYear, viewMonth - 1, 1).getDay();
  const daysInMonth = new Date(viewYear, viewMonth, 0).getDate();
  const weekDays = ['日', '一', '二', '三', '四', '五', '六'];
  const monthNames = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月'];

  const formatDateStr = (day: number) => {
    return `${viewYear}-${String(viewMonth).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
  };

  const calendarCells: (number | null)[] = [];
  for (let i = 0; i < firstDay; i++) calendarCells.push(null);
  for (let d = 1; d <= daysInMonth; d++) calendarCells.push(d);

  return (
    <div className="min-h-screen bg-paper">
      <Header title="历史日报" date={`${viewYear}年${viewMonth}月`} />

      <main className="max-w-4xl mx-auto px-4 py-6 flex flex-col lg:flex-row gap-6">
        {/* 左侧日历 */}
        <div className="lg:w-80 flex-shrink-0">
          {/* 月份导航 */}
          <div className="flex items-center justify-between mb-4">
            <button onClick={goPrevMonth}
              className="px-3 py-1 text-sm text-ink-light hover:text-ink-dark border border-border rounded">
              ← 上月
            </button>
            <h2 className="text-lg font-bold text-ink-dark">{viewYear}年 {monthNames[viewMonth - 1]}</h2>
            <button onClick={goNextMonth}
              className="px-3 py-1 text-sm text-ink-light hover:text-ink-dark border border-border rounded">
              下月 →
            </button>
          </div>

          {/* 星期表头 */}
          <div className="grid grid-cols-7 gap-1 mb-1">
            {weekDays.map((wd) => (
              <div key={wd} className="text-center text-xs text-ink-light py-1">{wd}</div>
            ))}
          </div>

          {/* 日期网格 */}
          <div className="grid grid-cols-7 gap-1">
            {calendarCells.map((day, idx) => {
              if (day === null) return <div key={`e-${idx}`} className="aspect-square" />;
              const dateStr = formatDateStr(day);
              const sessions = dateMap.get(dateStr);
              const hasMorning = sessions?.includes('morning');
              const hasEvening = sessions?.includes('evening');
              const isSelected = selectedDate === dateStr;
              const isToday = formatDateStr(today.getDate()) === dateStr &&
                viewYear === today.getFullYear() && viewMonth === today.getMonth() + 1;

              return (
                <button key={dateStr} onClick={() => handleDateClick(dateStr)}
                  className={`aspect-square flex flex-col items-center justify-center rounded-lg text-sm transition-colors relative ${
                    isSelected ? 'bg-ink-dark text-white' : isToday ? 'bg-card border border-border' : 'hover:bg-card'
                  } ${!sessions ? 'text-ink-light' : 'text-ink-dark'}`}
                >
                  <span>{day}</span>
                  {sessions && (
                    <div className="flex gap-0.5 mt-0.5">
                      {hasMorning && <span className={`w-1.5 h-1.5 rounded-full ${isSelected ? 'bg-yellow-300' : 'bg-yellow-500'}`} />}
                      {hasEvening && <span className={`w-1.5 h-1.5 rounded-full ${isSelected ? 'bg-blue-300' : 'bg-blue-500'}`} />}
                    </div>
                  )}
                </button>
              );
            })}
          </div>

          {/* 图例 */}
          <div className="flex gap-4 mt-3 text-xs text-ink-light">
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-yellow-500" /> 早报</span>
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-blue-500" /> 晚报</span>
          </div>
        </div>

        {/* 右侧日报详情 */}
        <div className="flex-1 min-w-0">
          {!selectedDate && !detailLoading && (
            <div className="flex items-center justify-center h-64 text-ink-light">
              <p>📅 点击日历中的日期查看历史日报</p>
            </div>
          )}

          {detailLoading && (
            <div className="flex items-center justify-center h-64 text-ink-light">
              <p>加载中...</p>
            </div>
          )}

          {!detailLoading && (detailReports.morning || detailReports.evening) && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {detailReports.morning && (
                <div>
                  <h3 className="text-base font-bold text-ink-dark mb-3 flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-yellow-500" />
                    ☀️ 早报 · {detailReports.morning.total_articles}篇
                  </h3>
                  <div className="flex flex-col gap-2">
                    {detailReports.morning.articles?.map((article) => (
                      <Card key={article.id} article={article} />
                    ))}
                  </div>
                </div>
              )}
              {detailReports.evening && (
                <div>
                  <h3 className="text-base font-bold text-ink-dark mb-3 flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-blue-500" />
                    🌙 晚报 · {detailReports.evening.total_articles}篇
                  </h3>
                  <div className="flex flex-col gap-2">
                    {detailReports.evening.articles?.map((article) => (
                      <Card key={article.id} article={article} />
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

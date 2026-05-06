import { useEffect, useState } from 'react';
import type { CalendarEntry } from '../api';
import { fetchCalendar } from '../api';

interface CalendarProps {
  selectedDate: string | null;
  onSelectDate: (dateStr: string) => void;
  compact?: boolean;
}

const WEEK_DAYS = ['日', '一', '二', '三', '四', '五', '六'];
const MONTH_NAMES = ['一月', '二月', '三月', '四月', '五月', '六月', '七月', '八月', '九月', '十月', '十一月', '十二月'];

export default function Calendar({ selectedDate, onSelectDate, compact }: CalendarProps) {
  const today = new Date();
  const [viewYear, setViewYear] = useState(today.getFullYear());
  const [viewMonth, setViewMonth] = useState(today.getMonth() + 1);
  const [calendarData, setCalendarData] = useState<CalendarEntry[]>([]);

  const dateMap = new Map<string, string[]>();
  calendarData.forEach((entry) => dateMap.set(entry.date, entry.sessions));

  useEffect(() => {
    fetchCalendar(viewYear, viewMonth).then(setCalendarData);
  }, [viewYear, viewMonth]);

  const goPrevMonth = () => {
    if (viewMonth === 1) {
      setViewYear(viewYear - 1);
      setViewMonth(12);
    } else {
      setViewMonth(viewMonth - 1);
    }
  };

  const goNextMonth = () => {
    if (viewMonth === 12) {
      setViewYear(viewYear + 1);
      setViewMonth(1);
    } else {
      setViewMonth(viewMonth + 1);
    }
  };

  const firstDay = new Date(viewYear, viewMonth - 1, 1).getDay();
  const daysInMonth = new Date(viewYear, viewMonth, 0).getDate();
  const fmt = (d: number) =>
    `${viewYear}-${String(viewMonth).padStart(2, '0')}-${String(d).padStart(2, '0')}`;

  const cells: (number | null)[] = [];
  for (let i = 0; i < firstDay; i++) cells.push(null);
  for (let d = 1; d <= daysInMonth; d++) cells.push(d);

  const cellSize = compact ? 'py-1' : 'py-1.5';

  return (
    <div className="bg-white rounded-xl border border-border shadow-sm overflow-hidden">
      {/* 月份导航 */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border">
        <button
          onClick={goPrevMonth}
          className="text-xs text-ink-light hover:text-ink-dark transition-colors"
        >
          ← 上月
        </button>
        <h3 className="text-sm font-bold text-ink-dark">
          {viewYear}年 {MONTH_NAMES[viewMonth - 1]}
        </h3>
        <button
          onClick={goNextMonth}
          className="text-xs text-ink-light hover:text-ink-dark transition-colors"
        >
          下月 →
        </button>
      </div>

      {/* 星期表头 */}
      <div className={`grid grid-cols-7 ${compact ? 'px-2 pt-2 pb-0' : 'px-3 pt-3 pb-1'}`}>
        {WEEK_DAYS.map((wd) => (
          <div key={wd} className="text-center text-xs font-medium text-ink-light">
            {wd}
          </div>
        ))}
      </div>

      {/* 日期网格 */}
      <div className={`grid grid-cols-7 ${compact ? 'px-2 pb-2 gap-0' : 'px-3 pb-3 gap-y-1'}`}>
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
              onClick={() => onSelectDate(dateStr)}
              className={`flex flex-col items-center ${cellSize} rounded-lg transition-all duration-150 relative`}
            >
              {isToday && !isSelected && (
                <div className="absolute inset-0 rounded-lg bg-card border border-border" />
              )}
              {isSelected && (
                <div className="absolute inset-0 rounded-lg bg-ink-dark" />
              )}

              <span
                className={`relative z-10 text-xs font-medium leading-tight ${
                  isSelected ? 'text-white' : isToday ? 'text-ink-dark' : 'text-ink-light'
                }`}
              >
                {day}
              </span>

              {sessions && (
                <div className="relative z-10 flex gap-0.5 mt-0.5">
                  {sessions.includes('morning') && (
                    <span
                      className={`text-[8px] px-0.5 rounded font-medium ${
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
                      className={`text-[8px] px-0.5 rounded font-medium ${
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
  );
}

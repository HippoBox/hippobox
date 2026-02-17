import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Activity } from 'lucide-react';
import { format, startOfYear, endOfYear, eachDayOfInterval, isSameDay, getDay } from 'date-fns';

import { Card } from '../Card';

export type ActivityPoint = {
    key: string;
    label: string;
    count: number;
    isToday?: boolean;
};

type ActivityChartCardProps = {
    series: ActivityPoint[];
    totalCount: number;
};

export function ActivityChartCard({ series, totalCount }: ActivityChartCardProps) {
    const { t } = useTranslation();
    const now = new Date();

    const { fullYearSeries, startPadding } = useMemo(() => {
        const start = startOfYear(now);
        const end = endOfYear(now);
        const allDays = eachDayOfInterval({ start, end });
        const dataMap = new Map(series.map((item) => [item.key, item]));

        const padding = getDay(start);
        const yearDays = allDays.map((day) => {
            const dateStr = format(day, 'yyyy-MM-dd');
            const existingData = dataMap.get(dateStr);
            return {
                key: dateStr,
                date: day,
                count: existingData?.count ?? 0,
                isToday: isSameDay(day, now),
            };
        });

        return { fullYearSeries: yearDays, startPadding: padding };
    }, [series, now]);

    const monthLabels = useMemo(() => {
        const labels: { name: string; pos: number }[] = [];
        let currentMonth = -1;
        const totalCols = Math.ceil((fullYearSeries.length + startPadding) / 7);

        fullYearSeries.forEach((day, index) => {
            const month = day.date.getMonth();
            if (month !== currentMonth) {
                currentMonth = month;
                const colIndex = Math.floor((index + startPadding) / 7);
                labels.push({ name: format(day.date, 'MMM'), pos: (colIndex / totalCols) * 100 });
            }
        });
        return labels.filter((label, i) => i === 0 || label.pos > labels[i - 1].pos + 3);
    }, [fullYearSeries, startPadding]);

    const getLevelClass = (knowledgeCount: number) => {
        if (knowledgeCount === 0) {
            return 'bg-slate-100 dark:bg-slate-800/50';
        } else if (knowledgeCount >= 1 && knowledgeCount <= 2) {
            return 'bg-[#eef4f9] dark:bg-[#293542]';
        } else if (knowledgeCount >= 3 && knowledgeCount <= 4) {
            return 'bg-[#d6e3ee] dark:bg-[#37495b]';
        } else if (knowledgeCount >= 5) {
            return 'bg-[#b2c6d4] dark:bg-[#4a6274]';
        }
    };

    return (
        <Card className="flex h-auto flex-col p-6 sm:p-7 overflow-hidden">
            <div className="flex flex-wrap items-start justify-between gap-3 mb-6">
                <div>
                    <h3 className="flex items-center gap-2 text-sm font-semibold">
                        <Activity
                            className="h-4 w-4 text-[color:var(--color-accent)]"
                            aria-hidden="true"
                        />
                        {t('main.dashboard.activityTitle')}
                    </h3>
                    <p className="mt-1 text-xs text-muted">
                        {t('main.dashboard.activitySubtitle', { year: now.getFullYear() })}
                    </p>
                </div>
                <span className="badge-chip">
                    {totalCount} {t('main.dashboard.entriesLabel')}
                </span>
            </div>

            <div className="flex-1 flex flex-col min-h-0">
                <div className="relative h-4 ml-7 mb-2">
                    {monthLabels.map((month) => (
                        <span
                            key={`${month.name}-${month.pos}`}
                            className="absolute text-[10px] text-muted-foreground whitespace-nowrap"
                            style={{ left: `${month.pos}%` }}
                        >
                            {month.name}
                        </span>
                    ))}
                </div>

                <div className="flex gap-3">
                    <div className="grid grid-rows-7 gap-1 text-[9px] text-muted-foreground py-0.5 w-4">
                        {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((day, i) => (
                            <div key={day} className="flex items-center justify-center">
                                {i % 2 === 1 ? day[0] : ''}
                            </div>
                        ))}
                    </div>

                    <div className="grid grid-rows-7 grid-flow-col gap-1 flex-1">
                        {Array.from({ length: startPadding }).map((_, i) => (
                            <div key={`pad-${i}`} className="aspect-square bg-transparent" />
                        ))}

                        {fullYearSeries.map((item) => {
                            return (
                                <div
                                    key={item.key}
                                    className={`aspect-square rounded-sm ${getLevelClass(item.count)} transition-all hover:scale-125 hover:z-10 cursor-pointer ${
                                        item.isToday
                                            ? 'ring-2 ring-[color:var(--color-accent)] ring-offset-2 ring-offset-[color:var(--color-surface)]'
                                            : ''
                                    }`}
                                    title={`${item.key}: ${item.count} knowledge`}
                                />
                            );
                        })}
                    </div>
                </div>

                <div className="flex items-center justify-end gap-2 mt-6 text-[10px] text-muted">
                    <span>Less</span>
                    <div className="flex gap-1">
                        {[0, 1, 3, 5].map((lvl) => (
                            <div
                                key={lvl}
                                className={`w-2.5 h-2.5 rounded-[1px] ${getLevelClass(lvl)}`}
                            />
                        ))}
                    </div>
                    <span>More</span>
                </div>
            </div>
        </Card>
    );
}

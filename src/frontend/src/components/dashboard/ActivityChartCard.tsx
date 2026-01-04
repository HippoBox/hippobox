import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Activity } from 'lucide-react';

import { Card } from '../Card';

export type ActivityPoint = {
    key: string;
    label: string;
    count: number;
};

type ActivityChartCardProps = {
    series: ActivityPoint[];
    totalCount: number;
};

export function ActivityChartCard({ series, totalCount }: ActivityChartCardProps) {
    const { t } = useTranslation();
    const maxActivity = useMemo(() => Math.max(...series.map((item) => item.count), 1), [series]);
    const gridLines = [25, 50, 75];

    return (
        <Card className="flex h-[360px] flex-col p-6 sm:p-7">
            <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                    <h3 className="flex items-center gap-2 text-sm font-semibold">
                        <Activity className="h-4 w-4" aria-hidden="true" />
                        {t('main.dashboard.activityTitle')}
                    </h3>
                    <p className="mt-1 text-xs text-muted">
                        {t('main.dashboard.activitySubtitle')}
                    </p>
                </div>
                <span className="badge-chip">{totalCount}</span>
            </div>
            <div className="relative mt-6 flex-1 overflow-hidden">
                <div className="absolute inset-0 rounded-2xl border border-[color:var(--color-border)] bg-[color:var(--color-surface)]/70 shadow-[0_16px_32px_rgba(15,23,42,0.08)]" />
                {gridLines.map((line) => (
                    <div
                        key={line}
                        className="pointer-events-none absolute inset-x-4 border-t border-dashed border-[color:var(--color-border)]/60"
                        style={{ top: `${100 - line}%` }}
                    />
                ))}
                <div className="relative flex h-full items-end gap-2 px-5 pb-4 pt-5">
                    {series.map((item) => (
                        <div key={item.key} className="flex flex-1 flex-col items-center gap-2">
                            <div
                                className="w-full rounded-full bg-[color:var(--color-accent)]/85 shadow-[0_10px_20px_rgba(249,115,22,0.25)] transition-all"
                                style={{
                                    height: `${Math.max(12, (item.count / maxActivity) * 100)}%`,
                                }}
                                title={`${item.label}: ${item.count}`}
                            />
                            <span className="text-[10px] text-muted whitespace-nowrap">
                                {item.label}
                            </span>
                        </div>
                    ))}
                </div>
            </div>
        </Card>
    );
}

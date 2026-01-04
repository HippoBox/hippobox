import { useTranslation } from 'react-i18next';
import { FolderKanban } from 'lucide-react';

import { Card } from '../Card';

export type TopicSummaryItem = {
    name: string;
    count: number;
    isDefault: boolean;
};

type TopicSummaryCardProps = {
    topics: TopicSummaryItem[];
};

export function TopicSummaryCard({ topics }: TopicSummaryCardProps) {
    const { t } = useTranslation();

    return (
        <Card className="flex h-[360px] flex-col p-6 sm:p-7">
            <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                    <h3 className="flex items-center gap-2 text-sm font-semibold">
                        <FolderKanban className="h-4 w-4" aria-hidden="true" />
                        {t('main.dashboard.topicsTitle')}
                    </h3>
                    <p className="mt-1 text-xs text-muted">{t('main.dashboard.topicsSubtitle')}</p>
                </div>
                <span className="badge-chip">{topics.length}</span>
            </div>
            <div className="scrollbar-theme mt-5 flex-1 grid grid-cols-2 auto-rows-[72px] gap-3 overflow-y-auto pr-2">
                {topics.length ? (
                    topics.map((topic) => (
                        <div
                            key={topic.name}
                            className="flex items-center justify-between rounded-2xl border border-[color:var(--color-border)] bg-[color:var(--color-surface)]/70 px-4 py-3"
                        >
                            <div className="flex items-center gap-3">
                                <span className="h-2 w-2 rounded-full bg-[color:var(--color-accent)]" />
                                <div>
                                    <div className="text-sm font-semibold">{topic.name}</div>
                                    {topic.isDefault ? (
                                        <div className="text-[11px] text-muted">
                                            {t('main.dashboard.defaultTopic')}
                                        </div>
                                    ) : null}
                                </div>
                            </div>
                            <div className="text-right">
                                <div className="text-sm font-semibold">{topic.count}</div>
                            </div>
                        </div>
                    ))
                ) : (
                    <p className="text-sm text-muted">{t('main.dashboard.topicsEmpty')}</p>
                )}
            </div>
        </Card>
    );
}

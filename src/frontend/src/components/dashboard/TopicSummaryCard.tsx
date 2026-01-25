import { useTranslation } from 'react-i18next';
import { FolderKanban, Trash2 } from 'lucide-react';

import { Card } from '../Card';

export type TopicSummaryItem = {
    id?: number;
    name: string;
    count: number;
    isDefault: boolean;
};

type TopicSummaryCardProps = {
    topics: TopicSummaryItem[];
    onDelete?: (topic: TopicSummaryItem) => void;
    deletingTopicId?: number | null;
};

export function TopicSummaryCard({ topics, onDelete, deletingTopicId }: TopicSummaryCardProps) {
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
                <span className="badge-chip">
                    {topics.length} {t('main.dashboard.topicsCountLabel')}
                </span>
            </div>
            <div className="scrollbar-theme mt-5 flex-1 grid grid-cols-2 auto-rows-[72px] gap-3 overflow-y-auto pr-2">
                {topics.length ? (
                    topics.map((topic) => {
                        const canDelete =
                            Boolean(onDelete) && !topic.isDefault && typeof topic.id === 'number';
                        const isDeleting = canDelete && deletingTopicId === topic.id;

                        return (
                            <div
                                key={topic.name}
                                className="flex items-center justify-between rounded-2xl border border-[color:var(--color-border)] bg-[color:var(--color-surface)]/70 px-4 py-3"
                            >
                                <div className="flex min-w-0 items-center gap-3">
                                    <span className="h-2 w-2 rounded-full bg-[color:var(--color-accent)]" />
                                    <div>
                                        <div className="flex flex-wrap items-center gap-2">
                                            <span className="text-sm font-semibold">
                                                {topic.name}
                                            </span>
                                            <span className="rounded-full border border-[color:var(--color-border)] bg-[color:var(--color-surface)]/80 px-2 py-0.5 text-[10px] font-semibold text-[color:var(--color-text)]">
                                                {topic.count}
                                            </span>
                                        </div>
                                        {topic.isDefault ? (
                                            <div className="text-[11px] text-muted">
                                                {t('main.dashboard.defaultTopic')}
                                            </div>
                                        ) : null}
                                    </div>
                                </div>
                                {canDelete ? (
                                    <button
                                        type="button"
                                        className="inline-flex items-center gap-1.5 rounded-full border border-rose-500/20 px-2.5 py-1 text-xs font-semibold text-rose-500 transition hover:border-rose-500/40 hover:bg-rose-500/10 disabled:opacity-60"
                                        onClick={() => onDelete?.(topic)}
                                        disabled={isDeleting}
                                        aria-label={t('main.dashboard.topicDelete')}
                                        title={t('main.dashboard.topicDelete')}
                                    >
                                        {isDeleting ? (
                                            <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-rose-300 border-t-rose-600" />
                                        ) : (
                                            <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                                        )}
                                        <span>{t('main.dashboard.topicDelete')}</span>
                                    </button>
                                ) : null}
                            </div>
                        );
                    })
                ) : (
                    <p className="text-sm text-muted">{t('main.dashboard.topicsEmpty')}</p>
                )}
            </div>
        </Card>
    );
}

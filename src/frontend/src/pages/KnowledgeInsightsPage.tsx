import { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { BarChart3 } from 'lucide-react';
import { useQueryClient } from '@tanstack/react-query';

import { ActivityChartCard } from '../components/dashboard/ActivityChartCard';
import { TopicSummaryCard } from '../components/dashboard/TopicSummaryCard';
import { ConfirmDialog } from '../components/ConfirmDialog';
import { ErrorMessage } from '../components/ErrorMessage';
import { useKnowledgeList } from '../context/KnowledgeListContext';
import { useDeleteTopicMutation, useTopicsQuery } from '../hooks/useTopics';

const formatDateKey = (date: Date) => {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
};

const formatActivityLabel = (date: Date, language: string) => {
    const month = date.getMonth() + 1;
    const day = date.getDate();
    if (language.startsWith('ko')) {
        return `${month}.${String(day).padStart(2, '0')}`;
    }
    return `${String(month).padStart(2, '0')}/${String(day).padStart(2, '0')}`;
};

const buildActivitySeries = (entries: Array<{ created_at?: string }>, language: string) => {
    const today = new Date();
    const todayKey = formatDateKey(today);

    const counts = new Map<string, number>();
    let minDate: Date | null = null;
    entries.forEach((entry) => {
        if (!entry.created_at) return;
        const parsed = new Date(entry.created_at);
        if (Number.isNaN(parsed.getTime())) return;
        const key = formatDateKey(parsed);
        counts.set(key, (counts.get(key) ?? 0) + 1);
        if (!minDate || parsed < minDate) {
            minDate = parsed;
        }
    });

    const start = minDate ? new Date(minDate) : new Date(today);
    start.setHours(0, 0, 0, 0);
    const end = new Date(today);
    end.setHours(0, 0, 0, 0);
    const totalDays = Math.max(
        1,
        Math.floor((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24)) + 1,
    );

    return Array.from({ length: totalDays }, (_, index) => {
        const current = new Date(start);
        current.setDate(start.getDate() + index);
        const key = formatDateKey(current);
        return {
            key,
            label: formatActivityLabel(current, language),
            count: counts.get(key) ?? 0,
            isToday: key === todayKey,
        };
    });
};

const extractErrorMessage = (error: unknown, fallback: string) => {
    if (!error) return fallback;
    if (typeof error === 'string') return error;
    if (error instanceof Error && error.message) return error.message;
    if (typeof error === 'object') {
        const payload = error as { message?: unknown; detail?: unknown };
        if (typeof payload.message === 'string') return payload.message;
        if (typeof payload.detail === 'string') return payload.detail;
        if (payload.detail && typeof payload.detail === 'object') {
            const detail = payload.detail as { message?: unknown };
            if (typeof detail.message === 'string') return detail.message;
        }
    }
    return fallback;
};

export function KnowledgeInsightsPage() {
    const { t, i18n } = useTranslation();
    const queryClient = useQueryClient();
    const { data: topics = [] } = useTopicsQuery();
    const { knowledge = [] } = useKnowledgeList();
    const [deleteTarget, setDeleteTarget] = useState<{
        id: number;
        name: string;
    } | null>(null);
    const [deleteError, setDeleteError] = useState('');

    const { mutate: deleteTopic, isPending: isDeletePending } = useDeleteTopicMutation({
        onSuccess: () => {
            setDeleteError('');
            setDeleteTarget(null);
        },
        onError: (error) => {
            setDeleteError(extractErrorMessage(error, t('main.dashboard.topicDeleteFailed')));
        },
    });

    const topicCounts = useMemo(() => {
        const counts = new Map<string, number>();
        knowledge.forEach((entry) => {
            counts.set(entry.topic, (counts.get(entry.topic) ?? 0) + 1);
        });
        return counts;
    }, [knowledge]);

    const topicRows = useMemo(() => {
        const fromTopics = topics.length
            ? topics.map((topic) => ({
                  id: topic.id,
                  name: topic.name,
                  count: topicCounts.get(topic.name) ?? 0,
                  isDefault: topic.is_default ?? false,
              }))
            : Array.from(topicCounts.entries()).map(([name, count]) => ({
                  name,
                  count,
                  isDefault: false,
              }));

        return fromTopics.sort((a, b) => {
            if (b.count !== a.count) return b.count - a.count;
            return a.name.localeCompare(b.name);
        });
    }, [topics, topicCounts]);

    const activitySeries = useMemo(() => {
        if (knowledge.length === 0) {
            return buildActivitySeries([], i18n.language);
        }
        return buildActivitySeries(knowledge, i18n.language);
    }, [knowledge, i18n.language]);
    const totalKnowledge = knowledge.length;

    useEffect(() => {
        queryClient.refetchQueries({ queryKey: ['topics'] });
        queryClient.refetchQueries({ queryKey: ['knowledge', 'list'] });
    }, [queryClient]);

    return (
        <div className="w-full space-y-10">
            <div className="space-y-1">
                <div className="flex items-center gap-3">
                    <BarChart3 className="h-5 w-5 text-muted" aria-hidden="true" />
                    <h2 className="font-display text-2xl font-semibold">
                        {t('knowledgeInsights.title')}
                    </h2>
                </div>
                <p className="max-w-2xl text-sm text-muted sm:text-base">
                    {t('knowledgeInsights.subtitle')}
                </p>
            </div>

            <div className="space-y-6">
                <div className="space-y-3">
                    <TopicSummaryCard
                        topics={topicRows}
                        onDelete={(topic) => {
                            if (!topic.id || topic.isDefault) return;
                            setDeleteError('');
                            setDeleteTarget({ id: topic.id, name: topic.name });
                        }}
                        deletingTopicId={isDeletePending ? (deleteTarget?.id ?? null) : null}
                    />
                    <ErrorMessage message={deleteError} />
                </div>
                <ActivityChartCard series={activitySeries} totalCount={totalKnowledge} />
            </div>
            <ConfirmDialog
                open={Boolean(deleteTarget)}
                title={t('main.dashboard.topicDeleteTitle')}
                description={t('main.dashboard.topicDeleteDescription', {
                    topic: deleteTarget?.name ?? '',
                })}
                confirmLabel={t('main.dashboard.topicDeleteConfirmButton')}
                cancelLabel={t('knowledgeContent.cancelButton')}
                onConfirm={() => {
                    if (!deleteTarget || isDeletePending) return;
                    deleteTopic(deleteTarget.id);
                }}
                onClose={() => {
                    setDeleteTarget(null);
                    setDeleteError('');
                }}
                isPending={isDeletePending}
            />
        </div>
    );
}

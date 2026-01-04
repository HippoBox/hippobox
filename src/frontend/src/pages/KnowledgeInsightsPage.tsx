import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { BarChart3 } from 'lucide-react';

import { ActivityChartCard } from '../components/dashboard/ActivityChartCard';
import { TopicSummaryCard } from '../components/dashboard/TopicSummaryCard';
import { useKnowledgeListQuery } from '../hooks/useKnowledge';
import { useTopicsQuery } from '../hooks/useTopics';

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

const buildActivitySeries = (
    entries: Array<{ created_at?: string }>,
    days: number,
    language: string,
) => {
    const today = new Date();
    const start = new Date(today);
    start.setDate(today.getDate() - (days - 1));

    const counts = new Map<string, number>();
    entries.forEach((entry) => {
        if (!entry.created_at) return;
        const parsed = new Date(entry.created_at);
        if (Number.isNaN(parsed.getTime())) return;
        const key = formatDateKey(parsed);
        counts.set(key, (counts.get(key) ?? 0) + 1);
    });

    return Array.from({ length: days }, (_, index) => {
        const current = new Date(start);
        current.setDate(start.getDate() + index);
        const key = formatDateKey(current);
        return {
            key,
            label: formatActivityLabel(current, language),
            count: counts.get(key) ?? 0,
        };
    });
};

export function KnowledgeInsightsPage() {
    const { t, i18n } = useTranslation();
    const { data: topics = [] } = useTopicsQuery();
    const { data: knowledge = [] } = useKnowledgeListQuery();

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

    const activitySeries = useMemo(
        () => buildActivitySeries(knowledge, 14, i18n.language),
        [knowledge, i18n.language],
    );
    const totalKnowledge = knowledge.length;

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
                <TopicSummaryCard topics={topicRows} />
                <ActivityChartCard series={activitySeries} totalCount={totalKnowledge} />
            </div>
        </div>
    );
}

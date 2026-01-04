import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Search } from 'lucide-react';

import { useKnowledgeListQuery } from '../../hooks/useKnowledge';
import { Input } from '../Input';

type KnowledgeSearchCardProps = {
    inputId?: string;
};

type SearchFilterKey = 'title' | 'topic' | 'tags' | 'content' | 'created_at' | 'updated_at';

const SEARCH_FILTERS: Array<{ key: SearchFilterKey; labelKey: string }> = [
    { key: 'title', labelKey: 'main.search.filters.title' },
    { key: 'topic', labelKey: 'main.search.filters.topic' },
    { key: 'tags', labelKey: 'main.search.filters.tags' },
    { key: 'content', labelKey: 'main.search.filters.content' },
    { key: 'created_at', labelKey: 'main.search.filters.createdAt' },
    { key: 'updated_at', labelKey: 'main.search.filters.updatedAt' },
];

const formatDate = (value: string | undefined) => {
    if (!value) return '-';
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return '-';
    const year = parsed.getFullYear();
    const month = String(parsed.getMonth() + 1).padStart(2, '0');
    const day = String(parsed.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
};

export function KnowledgeSearchCard({ inputId }: KnowledgeSearchCardProps) {
    const { t } = useTranslation();
    const { data: knowledgeList = [] } = useKnowledgeListQuery();
    const [query, setQuery] = useState('');
    const [selectedFilters, setSelectedFilters] = useState<Set<SearchFilterKey>>(
        () => new Set(SEARCH_FILTERS.map((filter) => filter.key)),
    );

    const defaultResults = useMemo(() => {
        return [...knowledgeList].sort((a, b) => {
            const aTime = a.created_at ? new Date(a.created_at).getTime() : 0;
            const bTime = b.created_at ? new Date(b.created_at).getTime() : 0;
            return bTime - aTime;
        });
    }, [knowledgeList]);

    const visibleResults = useMemo(() => {
        const trimmed = query.trim();
        if (!trimmed) return defaultResults;
        const isTagOnly = trimmed.startsWith('#');
        const activeFilters =
            selectedFilters.size === 0
                ? new Set(SEARCH_FILTERS.map((filter) => filter.key))
                : selectedFilters;
        const terms = trimmed
            .split(/\s+/)
            .map((term) => term.trim())
            .filter(Boolean)
            .map((term) => (isTagOnly ? term.replace(/^#+/, '') : term))
            .map((term) => term.toLowerCase())
            .filter(Boolean);
        if (!terms.length) return defaultResults;
        return defaultResults.filter((item) => {
            if (isTagOnly) {
                const tags = (item.tags ?? []).map((tag) => tag.toLowerCase());
                return terms.every((term) => tags.some((tag) => tag.includes(term)));
            }
            const fields: string[] = [];
            if (activeFilters.has('title')) fields.push(item.title);
            if (activeFilters.has('topic')) fields.push(item.topic);
            if (activeFilters.has('content')) fields.push(item.content);
            if (activeFilters.has('tags')) fields.push(...(item.tags ?? []));
            if (activeFilters.has('created_at')) fields.push(item.created_at ?? '');
            if (activeFilters.has('updated_at')) fields.push(item.updated_at ?? '');
            const haystack = fields.join(' ').toLowerCase();
            return terms.every((term) => haystack.includes(term));
        });
    }, [defaultResults, query, selectedFilters]);

    const handleFilterToggle = (key: SearchFilterKey) => {
        setSelectedFilters((prev) => {
            const next = new Set(prev);
            if (next.has(key)) {
                next.delete(key);
            } else {
                next.add(key);
            }
            return next;
        });
    };

    return (
        <div className="w-full space-y-6">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-end">
                <div className="flex-1">
                    <Input
                        id={inputId ?? 'knowledge-search'}
                        placeholder={t('main.search.placeholder')}
                        value={query}
                        leadingIcon={<Search className="h-4 w-4" aria-hidden="true" />}
                        onChange={(event) => {
                            setQuery(event.target.value);
                        }}
                    />
                </div>
                <div className="flex flex-wrap items-center gap-2 sm:justify-end">
                    {SEARCH_FILTERS.map((filter) => {
                        const isActive = selectedFilters.has(filter.key);
                        return (
                            <button
                                key={filter.key}
                                type="button"
                                onClick={() => handleFilterToggle(filter.key)}
                                className={[
                                    'h-11 w-24 rounded-full border text-[11px] font-semibold uppercase tracking-[0.12em] transition',
                                    isActive
                                        ? 'border-[color:var(--color-border-strong)] bg-[color:var(--color-surface)] text-[color:var(--color-text)]'
                                        : 'border-[color:var(--color-border)] bg-transparent text-muted',
                                ]
                                    .filter(Boolean)
                                    .join(' ')}
                            >
                                {t(filter.labelKey)}
                            </button>
                        );
                    })}
                </div>
            </div>
            <div className="grid gap-4">
                {visibleResults.length ? (
                    visibleResults.map((item) => (
                        <div
                            key={item.id}
                            className="rounded-2xl border border-[color:var(--color-border)] bg-[color:var(--color-surface)]/70 px-4 py-3"
                        >
                            <div className="flex flex-wrap items-center gap-2">
                                <div className="text-sm font-semibold">{item.title}</div>
                                <div className="flex flex-wrap items-center gap-1">
                                    {item.tags?.length ? (
                                        item.tags.map((tag) => (
                                            <span
                                                key={`${item.id}-${tag}`}
                                                className="inline-flex items-center rounded-full border border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-2 py-0.5 text-[10px] font-semibold text-[color:var(--color-text)]"
                                            >
                                                #{tag}
                                            </span>
                                        ))
                                    ) : (
                                        <span className="inline-flex items-center rounded-full border border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-2 py-0.5 text-[10px] text-muted">
                                            {t('main.search.noTags')}
                                        </span>
                                    )}
                                </div>
                            </div>
                            <div className="mt-1 text-[11px] text-muted">{item.topic}</div>
                            <p className="mt-4 mb-5 min-h-[3.75rem] text-xs text-muted line-clamp-3">
                                {item.content}
                            </p>
                            <div className="mt-3 flex flex-wrap gap-2">
                                <span className="inline-flex items-center rounded-full border border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-2 py-1 text-[10px] text-muted">
                                    {t('main.search.createdAt')} {formatDate(item.created_at)}
                                </span>
                                <span className="inline-flex items-center rounded-full border border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-2 py-1 text-[10px] text-muted">
                                    {t('main.search.updatedAt')} {formatDate(item.updated_at)}
                                </span>
                            </div>
                        </div>
                    ))
                ) : (
                    <p className="text-sm text-muted">{t('main.search.empty')}</p>
                )}
            </div>
        </div>
    );
}

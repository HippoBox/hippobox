import { useEffect, useMemo, useRef, useState, type MouseEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { Search } from 'lucide-react';
import { Link } from 'react-router-dom';
import { marked } from 'marked';

import { useKnowledgeList } from '../../context/KnowledgeListContext';
import { useTheme } from '../../context/ThemeContext';
import { apiClient } from '../../api/client';
import type { KnowledgeResponse } from '../../hooks/useKnowledge';
import { useVdbEnabled } from '../../hooks/useFeatures';
import { Button } from '../Button';
import { ErrorMessage } from '../ErrorMessage';
import { Input } from '../Input';
import { LoadingPage } from '../../pages/LoadingPage';

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

const PREVIEW_LIMIT = 200;
const NO_TOPIC_KEY = '__no_topic__';
const SEARCH_STATE_STORAGE_KEY = 'hippobox_knowledge_search_state';

const toPlainText = (markdown: string) => {
    if (!markdown.trim()) return '';
    const parsed = marked.parse(markdown, {
        breaks: true,
        gfm: true,
    });
    const html = typeof parsed === 'string' ? parsed : markdown;
    const doc = new DOMParser().parseFromString(html, 'text/html');
    const text = doc.body.textContent ?? '';
    return text.replace(/\s+/g, ' ').trim();
};

const truncateText = (value: string, maxLength: number) => {
    if (value.length <= maxLength) return value;
    const chars = Array.from(value);
    if (chars.length <= maxLength) return value;
    return `${chars.slice(0, maxLength).join('')}...`;
};

type TopicRow = {
    key: string;
    label: string;
    count: number;
};

type StoredSearchState = {
    query?: string;
    hyperQuery?: string;
    hyperSubmittedQuery?: string;
    hyperResults?: KnowledgeResponse[];
    activeTopic?: string | null;
    selectedFilters?: SearchFilterKey[];
};

const loadStoredSearchState = (): StoredSearchState | null => {
    if (typeof window === 'undefined') return null;
    try {
        const raw = window.localStorage.getItem(SEARCH_STATE_STORAGE_KEY);
        if (!raw) return null;
        const parsed = JSON.parse(raw) as StoredSearchState;
        if (!parsed || typeof parsed !== 'object') return null;
        return parsed;
    } catch {
        return null;
    }
};

const sanitizeStoredFilters = (filters?: SearchFilterKey[]) => {
    if (!Array.isArray(filters)) return null;
    const allowed = new Set(SEARCH_FILTERS.map((filter) => filter.key));
    const sanitized = filters.filter((key) => allowed.has(key));
    return sanitized.length ? sanitized : null;
};

export function KnowledgeSearchCard({ inputId }: KnowledgeSearchCardProps) {
    const { t } = useTranslation();
    const { knowledge: knowledgeList = [] } = useKnowledgeList();
    const { theme } = useTheme();
    const { vdbEnabled } = useVdbEnabled();
    const storedState = loadStoredSearchState();
    const storedFilters = sanitizeStoredFilters(storedState?.selectedFilters);
    const [query, setQuery] = useState(storedState?.query ?? '');
    const [hyperQuery, setHyperQuery] = useState(storedState?.hyperQuery ?? '');
    const [hyperSubmittedQuery, setHyperSubmittedQuery] = useState(
        storedState?.hyperSubmittedQuery ?? '',
    );
    const [hyperResults, setHyperResults] = useState<KnowledgeResponse[]>(
        storedState?.hyperResults ?? [],
    );
    const [hyperPending, setHyperPending] = useState(false);
    const [hyperError, setHyperError] = useState('');
    const [hyperSearchEnabled, setHyperSearchEnabled] = useState(false);
    const [activeTopic, setActiveTopic] = useState<string | null>(
        storedState?.activeTopic ?? null,
    );
    const [selectedFilters, setSelectedFilters] = useState<Set<SearchFilterKey>>(
        () =>
            new Set(
                storedFilters?.length
                    ? storedFilters
                    : SEARCH_FILTERS.map((filter) => filter.key),
            ),
    );
    const hyperRequestIdRef = useRef(0);

    const isHyperActive = vdbEnabled && hyperSubmittedQuery.trim().length > 0;
    const hippoIconSrc = theme === 'dark' ? '/hipposearch-white.svg' : '/hipposearch-black.svg';

    const defaultResults = useMemo(() => {
        return [...knowledgeList].sort((a, b) => {
            const aTime = a.created_at ? new Date(a.created_at).getTime() : 0;
            const bTime = b.created_at ? new Date(b.created_at).getTime() : 0;
            return bTime - aTime;
        });
    }, [knowledgeList]);

    const filterByActiveTopic = (items: KnowledgeResponse[]) => {
        if (!activeTopic) return items;
        return items.filter((item) => {
            const raw = item.topic?.trim() ?? '';
            const normalized = raw.toLowerCase();
            if (activeTopic === NO_TOPIC_KEY) {
                return !normalized || normalized === 'uncategorized';
            }
            return normalized === activeTopic;
        });
    };

    const baseResults = useMemo(() => {
        return isHyperActive ? hyperResults : defaultResults;
    }, [defaultResults, hyperResults, isHyperActive]);

    const visibleResults = useMemo(() => {
        const trimmed = query.trim();
        let results = baseResults;
        if (trimmed) {
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
            if (terms.length) {
                results = results.filter((item) => {
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
            }
        }
        return filterByActiveTopic(results);
    }, [baseResults, query, selectedFilters, activeTopic]);
    const displayResults = visibleResults;

    const previewById = useMemo(() => {
        const map = new Map<number, string>();
        displayResults.forEach((item) => {
            const plain = toPlainText(item.content ?? '');
            map.set(item.id, truncateText(plain, PREVIEW_LIMIT));
        });
        return map;
    }, [displayResults]);

    const topicRows = useMemo<TopicRow[]>(() => {
        const rows = new Map<string, TopicRow>();
        baseResults.forEach((item) => {
            const raw = item.topic?.trim() ?? '';
            const normalized = raw.toLowerCase();
            const isEmpty = !raw || normalized === 'uncategorized';
            const key = isEmpty ? NO_TOPIC_KEY : normalized;
            const label = isEmpty ? t('knowledgeContent.noTopic') : raw;
            const existing = rows.get(key);
            if (existing) {
                existing.count += 1;
            } else {
                rows.set(key, { key, label, count: 1 });
            }
        });

        return Array.from(rows.values()).sort((a, b) => {
            if (a.key === NO_TOPIC_KEY && b.key !== NO_TOPIC_KEY) return 1;
            if (b.key === NO_TOPIC_KEY && a.key !== NO_TOPIC_KEY) return -1;
            if (b.count !== a.count) return b.count - a.count;
            return a.label.localeCompare(b.label);
        });
    }, [baseResults, t]);

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

    const handleTagClick = (event: MouseEvent<HTMLButtonElement>, tag: string) => {
        event.preventDefault();
        event.stopPropagation();
        setQuery(`#${tag}`);
    };

    const handleTopicClick = (event: MouseEvent<HTMLButtonElement>, key: string) => {
        event.preventDefault();
        setActiveTopic((prev) => (prev === key ? null : key));
    };

    const handleHyperSubmit = () => {
        const trimmed = hyperQuery.trim();
        if (!trimmed) {
            setHyperSubmittedQuery('');
            setHyperSearchEnabled(false);
            return;
        }
        setHyperSearchEnabled(true);
        setHyperSubmittedQuery(trimmed);
    };

    const handleHyperReset = () => {
        hyperRequestIdRef.current += 1;
        setQuery('');
        setActiveTopic(null);
        setHyperQuery('');
        setHyperSubmittedQuery('');
        setHyperResults([]);
        setHyperError('');
        setHyperPending(false);
        setHyperSearchEnabled(false);
    };

    useEffect(() => {
        if (!vdbEnabled) {
            hyperRequestIdRef.current += 1;
            setHyperQuery('');
            setHyperSubmittedQuery('');
            setHyperResults([]);
            setHyperError('');
            setHyperPending(false);
            return;
        }
        const trimmed = hyperSubmittedQuery.trim();
        if (!trimmed) {
            hyperRequestIdRef.current += 1;
            setHyperResults([]);
            setHyperError('');
            setHyperPending(false);
            return;
        }
        if (!hyperSearchEnabled) return;

        const requestId = hyperRequestIdRef.current + 1;
        hyperRequestIdRef.current = requestId;
        const timeoutId = window.setTimeout(async () => {
            setHyperPending(true);
            setHyperError('');
            setHyperResults([]);
            try {
                const { data, error } = await apiClient.GET('/api/v1/knowledge/search', {
                    params: {
                        query: {
                            query: trimmed,
                            limit: 5,
                        },
                    },
                });
                if (hyperRequestIdRef.current !== requestId) return;
                if (error) {
                    setHyperResults([]);
                    setHyperError(t('main.search.failed'));
                } else {
                    setHyperResults(data ?? []);
                }
            } catch {
                if (hyperRequestIdRef.current !== requestId) return;
                setHyperResults([]);
                setHyperError(t('main.search.failed'));
            } finally {
                if (hyperRequestIdRef.current === requestId) {
                    setHyperPending(false);
                }
            }
        }, 350);

        return () => {
            window.clearTimeout(timeoutId);
        };
    }, [hyperSearchEnabled, hyperSubmittedQuery, t, vdbEnabled]);

    useEffect(() => {
        if (typeof window === 'undefined') return;
        const payload: StoredSearchState = {
            query,
            hyperQuery,
            hyperSubmittedQuery,
            hyperResults,
            activeTopic,
            selectedFilters: Array.from(selectedFilters),
        };
        try {
            window.localStorage.setItem(SEARCH_STATE_STORAGE_KEY, JSON.stringify(payload));
        } catch {
            // ignore storage errors
        }
    }, [query, hyperQuery, hyperSubmittedQuery, activeTopic, selectedFilters]);

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
            {vdbEnabled ? (
                <div className="space-y-2">
                    <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
                        <div className="flex-1">
                            <div className="hippo-search-shell">
                                <div className="hippo-search-inner">
                                    <Input
                                        id={`${inputId ?? 'knowledge-search'}-hyper`}
                                        placeholder={t('main.search.hyperPlaceholder')}
                                        value={hyperQuery}
                                        leadingIcon={
                                            <img
                                                src={hippoIconSrc}
                                                alt=""
                                                className="h-5 w-5 object-contain"
                                                aria-hidden="true"
                                            />
                                        }
                                        className="hippo-search-text input-field--borderless bg-transparent shadow-none focus:shadow-none focus:border-transparent"
                                        onKeyDown={(event) => {
                                            if (event.key === 'Enter') {
                                                event.preventDefault();
                                                handleHyperSubmit();
                                            }
                                        }}
                                        onChange={(event) => {
                                            const next = event.target.value;
                                            setHyperQuery(next);
                                            if (!next.trim()) {
                                                setHyperSubmittedQuery('');
                                            }
                                        }}
                                    />
                                </div>
                            </div>
                        </div>
                        <div className="flex flex-wrap gap-2 sm:justify-end">
                            <Button
                                type="button"
                                className="h-11 whitespace-nowrap"
                                disabled={hyperPending || !hyperQuery.trim()}
                                onClick={handleHyperSubmit}
                            >
                                {t('main.search.button')}
                            </Button>
                            <Button
                                type="button"
                                variant="outline"
                                className="h-11 whitespace-nowrap"
                                disabled={hyperPending && isHyperActive}
                                onClick={handleHyperReset}
                            >
                                {t('main.search.showAll')}
                            </Button>
                        </div>
                    </div>
                    {hyperPending && isHyperActive ? <LoadingPage variant="content" /> : null}
                    {hyperError ? <ErrorMessage message={hyperError} /> : null}
                </div>
            ) : null}
            <div className="grid gap-4">
                {displayResults.length ? (
                    displayResults.map((item) => (
                        <Link
                            key={item.id}
                            to={`/app/knowledge/${item.id}`}
                            aria-label={t('main.search.openLabel', { title: item.title })}
                            className="group block rounded-2xl border border-[color:var(--color-border)] bg-[color:var(--color-surface)]/70 px-4 py-3 text-[color:var(--color-text)] no-underline transition hover:-translate-y-0.5 hover:border-[color:var(--color-border-strong)] hover:shadow-[0_12px_30px_rgba(15,23,42,0.12)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--color-accent)]"
                        >
                            <div className="flex flex-wrap items-center gap-2">
                                <div className="text-sm font-semibold">{item.title}</div>
                                <div className="flex flex-wrap items-center gap-1">
                                    {item.tags?.length ? (
                                        item.tags.map((tag) => (
                                            <button
                                                key={`${item.id}-${tag}`}
                                                type="button"
                                                onClick={(event) => handleTagClick(event, tag)}
                                                className="inline-flex items-center rounded-full border border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-2 py-0.5 text-[10px] font-semibold text-[color:var(--color-text)] transition hover:border-[color:var(--color-border-strong)]"
                                            >
                                                #{tag}
                                            </button>
                                        ))
                                    ) : (
                                        <span className="inline-flex items-center rounded-full border border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-2 py-0.5 text-[10px] text-muted">
                                            {t('main.search.noTags')}
                                        </span>
                                    )}
                                </div>
                            </div>
                            <div className="mt-1 text-[11px] text-muted">{item.topic}</div>
                            <p className="mt-4 mb-5 h-[3.75rem] text-xs text-muted line-clamp-3">
                                {previewById.get(item.id) ?? ''}
                            </p>
                            <div className="mt-3 flex flex-wrap gap-2">
                                <span className="inline-flex items-center rounded-full border border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-2 py-1 text-[10px] text-muted">
                                    {t('main.search.createdAt')} {formatDate(item.created_at)}
                                </span>
                                <span className="inline-flex items-center rounded-full border border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-2 py-1 text-[10px] text-muted">
                                    {t('main.search.updatedAt')} {formatDate(item.updated_at)}
                                </span>
                            </div>
                        </Link>
                    ))
                ) : hyperPending && isHyperActive ? null : (
                    <p className="text-sm text-muted">{t('main.search.empty')}</p>
                )}
            </div>
            {topicRows.length ? (
                <aside className="hidden xl:block">
                    <div
                        className="rounded-2xl bg-[color:var(--color-surface)]/70 p-4 xl:fixed xl:top-40 xl:w-56"
                        style={{
                            left: 'max(1rem, calc(50% - 36rem - 17rem))',
                        }}
                    >
                        <div className="mb-3 text-[11px] font-semibold uppercase tracking-[0.12em] text-[color:var(--color-text)]">
                            {t('knowledgeContent.meta.topic')}
                        </div>
                        <nav className="space-y-2" aria-label={t('knowledgeContent.meta.topic')}>
                            {topicRows.map((topic) => {
                                const isActive = activeTopic === topic.key;
                                return (
                                    <button
                                        key={topic.key}
                                        type="button"
                                        onClick={(event) => handleTopicClick(event, topic.key)}
                                        className={[
                                            'flex w-32 items-center justify-between gap-2 rounded-lg border px-2.5 py-1.5 text-left text-sm transition',
                                            isActive
                                                ? 'border-[color:var(--color-border-strong)] bg-[color:var(--color-surface)] text-[color:var(--color-text)]'
                                                : 'border-transparent text-muted hover:border-[color:var(--color-border)] hover:text-[color:var(--color-text)]',
                                        ]
                                            .filter(Boolean)
                                            .join(' ')}
                                    >
                                        <span className="min-w-0 flex-1 truncate">
                                            {topic.label}
                                        </span>
                                        <span className="shrink-0 text-[11px] text-muted">
                                            {topic.count}
                                        </span>
                                    </button>
                                );
                            })}
                        </nav>
                    </div>
                </aside>
            ) : null}
        </div>
    );
}

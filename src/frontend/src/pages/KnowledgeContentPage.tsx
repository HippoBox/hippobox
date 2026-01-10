import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, BookOpen, PencilLine } from 'lucide-react';

import { Button } from '../components/Button';
import { Card } from '../components/Card';
import { MarkdownContent } from '../components/MarkdownContent';
import { useKnowledgeList } from '../contexts/KnowledgeListContext';

const formatDate = (value: string | undefined) => {
    if (!value) return '-';
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return '-';
    const year = parsed.getFullYear();
    const month = String(parsed.getMonth() + 1).padStart(2, '0');
    const day = String(parsed.getDate()).padStart(2, '0');
    return `${year}.${month}.${day}`;
};

export function KnowledgeContentPage() {
    const { t } = useTranslation();
    const { knowledgeId } = useParams();
    const { knowledge = [], isPending, isError } = useKnowledgeList();

    const entry = useMemo(() => {
        if (!knowledgeId) return undefined;
        return knowledge.find((item) => String(item.id) === knowledgeId);
    }, [knowledge, knowledgeId]);

    if (isPending) {
        return (
            <div className="flex min-h-[40vh] items-center justify-center">
                <span className="badge-chip">{t('knowledgeContent.loading')}</span>
            </div>
        );
    }

    return (
        <div className="w-full space-y-10">
            {isError ? (
                <Card className="p-8 text-center bg-transparent backdrop-blur-0 shadow-none border-transparent">
                    <div className="flex justify-end">
                        <Link to="/app" className="shrink-0">
                            <Button type="button" variant="outline" className="h-10 px-4 text-xs">
                                <span className="flex items-center gap-2">
                                    <ArrowLeft className="h-4 w-4" aria-hidden="true" />
                                    {t('knowledgeContent.back')}
                                </span>
                            </Button>
                        </Link>
                    </div>
                    <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full border border-[color:var(--color-border)] bg-[color:var(--color-surface)]">
                        <BookOpen className="h-5 w-5 text-muted" aria-hidden="true" />
                    </div>
                    <h3 className="mt-4 text-lg font-semibold">
                        {t('knowledgeContent.loadFailed')}
                    </h3>
                    <p className="mt-2 text-sm text-muted">
                        {t('knowledgeContent.loadFailedHint')}
                    </p>
                </Card>
            ) : entry ? (
                <Card
                    className="space-y-6 p-8 bg-transparent backdrop-blur-0 shadow-none border-transparent"
                    variant="strong"
                >
                    <div className="space-y-2">
                        <div className="text-xs text-muted">
                            {t('knowledgeContent.meta.createdAt')} {formatDate(entry.created_at)} ·{' '}
                            {t('knowledgeContent.meta.updatedAt')} {formatDate(entry.updated_at)}
                        </div>
                        <div className="flex flex-wrap items-center justify-between gap-3">
                            <div className="flex min-w-0 flex-wrap items-center gap-3">
                                <h3 className="font-display text-3xl font-semibold">
                                    {entry.title}
                                </h3>
                                <p className="text-sm text-muted">{entry.topic}</p>
                            </div>
                            <div className="flex shrink-0 items-center gap-2">
                                <Button type="button" className="h-10 px-4 text-xs">
                                    <span className="flex items-center gap-2">
                                        <PencilLine className="h-4 w-4" aria-hidden="true" />
                                        {t('knowledgeContent.edit')}
                                    </span>
                                </Button>
                                <Link to="/app" className="shrink-0">
                                    <Button
                                        type="button"
                                        variant="outline"
                                        className="h-10 px-4 text-xs"
                                    >
                                        <span className="flex items-center gap-2">
                                            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
                                            {t('knowledgeContent.back')}
                                        </span>
                                    </Button>
                                </Link>
                            </div>
                        </div>
                        <div className="flex flex-wrap gap-2">
                            {entry.tags?.length ? (
                                entry.tags.map((tag) => (
                                    <span
                                        key={`${entry.id}-${tag}`}
                                        className="inline-flex items-center rounded-full border border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-2 py-1 text-[10px] font-semibold text-[color:var(--color-text)]"
                                    >
                                        #{tag}
                                    </span>
                                ))
                            ) : (
                                <span className="inline-flex items-center rounded-full border border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-2 py-1 text-[10px] text-muted">
                                    {t('knowledgeContent.noTags')}
                                </span>
                            )}
                        </div>
                    </div>

                    <div className="p-3">
                        {entry.content?.trim() ? (
                            <MarkdownContent content={entry.content} />
                        ) : (
                            <p className="text-sm text-muted">
                                {t('knowledgeContent.emptyContent')}
                            </p>
                        )}
                    </div>
                </Card>
            ) : (
                <Card className="p-8 text-center bg-transparent backdrop-blur-0 shadow-none border-transparent">
                    <div className="flex justify-end">
                        <Link to="/app" className="shrink-0">
                            <Button type="button" variant="outline" className="h-10 px-4 text-xs">
                                <span className="flex items-center gap-2">
                                    <ArrowLeft className="h-4 w-4" aria-hidden="true" />
                                    {t('knowledgeContent.back')}
                                </span>
                            </Button>
                        </Link>
                    </div>
                    <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full border border-[color:var(--color-border)] bg-[color:var(--color-surface)]">
                        <BookOpen className="h-5 w-5 text-muted" aria-hidden="true" />
                    </div>
                    <h3 className="mt-4 text-lg font-semibold">
                        {t('knowledgeContent.notFoundTitle')}
                    </h3>
                    <p className="mt-2 text-sm text-muted">{t('knowledgeContent.notFoundHint')}</p>
                </Card>
            )}
        </div>
    );
}

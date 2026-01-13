import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, BookOpen, PencilLine, Trash2 } from 'lucide-react';

import { Button } from '../components/Button';
import { Card } from '../components/Card';
import { ConfirmDialog } from '../components/ConfirmDialog';
import { ErrorMessage } from '../components/ErrorMessage';
import { MarkdownContent } from '../components/MarkdownContent';
import { useKnowledgeList } from '../contexts/KnowledgeListContext';
import { useDeleteKnowledgeMutation, useKnowledgeQuery } from '../hooks/useKnowledge';
import { extractHeadings } from '../utils/markdown';

const formatDate = (value: string | undefined) => {
    if (!value) return '-';
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return '-';
    const year = parsed.getFullYear();
    const month = String(parsed.getMonth() + 1).padStart(2, '0');
    const day = String(parsed.getDate()).padStart(2, '0');
    return `${year}.${month}.${day}`;
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

export function KnowledgeContentPage() {
    const { t } = useTranslation();
    const { knowledgeId } = useParams();
    const navigate = useNavigate();
    const { knowledge = [], isPending, isError } = useKnowledgeList();
    const [deleteError, setDeleteError] = useState('');
    const [showDeleteDialog, setShowDeleteDialog] = useState(false);

    const listEntry = useMemo(() => {
        if (!knowledgeId) return undefined;
        return knowledge.find((item) => String(item.id) === knowledgeId);
    }, [knowledge, knowledgeId]);
    const numericKnowledgeId = knowledgeId ? Number(knowledgeId) : undefined;
    const {
        data: directEntry,
        isPending: isDirectPending,
        isError: isDirectError,
    } = useKnowledgeQuery(numericKnowledgeId, {
        enabled: Boolean(knowledgeId),
        refetchOnMount: 'always',
        staleTime: 0,
    });
    const entry = directEntry ?? listEntry;
    const isLoading = (isPending || isDirectPending) && !entry;
    const hasError = (isError || isDirectError) && !entry;
    const headings = useMemo(() => extractHeadings(entry?.content ?? ''), [entry?.content]);
    const showToc = headings.length > 0;
    const { mutate: deleteKnowledge, isPending: isDeletePending } = useDeleteKnowledgeMutation({
        onSuccess: () => {
            setDeleteError('');
            setShowDeleteDialog(false);
            navigate('/app');
        },
        onError: (error) => {
            setDeleteError(extractErrorMessage(error, t('knowledgeContent.deleteFailed')));
        },
    });

    if (isLoading) {
        return (
            <div className="flex min-h-[40vh] items-center justify-center">
                <span className="badge-chip">{t('knowledgeContent.loading')}</span>
            </div>
        );
    }

    const handleHeadingClick = (headingId: string) => {
        const target = document.getElementById(headingId);
        if (!target) return;
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        if (typeof window !== 'undefined') {
            window.history.replaceState(null, '', `#${headingId}`);
        }
    };

    return (
        <div className="w-full space-y-10">
            {hasError ? (
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
                <>
                    <Card
                        className="space-y-6 p-8 bg-transparent backdrop-blur-0 shadow-none border-transparent knowledge-content-card"
                        variant="strong"
                    >
                        <div className="space-y-2">
                            <div className="text-xs text-muted">
                                {t('knowledgeContent.meta.createdAt')}{' '}
                                {formatDate(entry.created_at)} ·{' '}
                                {t('knowledgeContent.meta.updatedAt')}{' '}
                                {formatDate(entry.updated_at)}
                            </div>
                            <div className="flex flex-wrap items-start justify-between gap-3">
                                <div className="min-w-0">
                                    <h3 className="font-display text-3xl font-semibold">
                                        {entry.title}
                                    </h3>
                                    <p className="text-sm text-muted truncate">
                                        {(() => {
                                            const rawTopic = entry.topic?.trim() ?? '';
                                            if (!rawTopic) return t('knowledgeContent.noTopic');
                                            if (rawTopic.toLowerCase() === 'uncategorized') {
                                                return t('knowledgeContent.noTopic');
                                            }
                                            return rawTopic;
                                        })()}
                                    </p>
                                </div>
                                <div className="ml-auto flex shrink-0 items-center gap-2">
                                    <Link
                                        to={`/app/knowledge/${entry.id}/edit`}
                                        className="shrink-0"
                                    >
                                        <Button type="button" className="h-10 px-4 text-xs">
                                            <span className="flex items-center gap-2">
                                                <PencilLine
                                                    className="h-4 w-4"
                                                    aria-hidden="true"
                                                />
                                                {t('knowledgeContent.edit')}
                                            </span>
                                        </Button>
                                    </Link>
                                    <Button
                                        type="button"
                                        variant="outline"
                                        className="h-10 px-4 text-xs"
                                        disabled={isDeletePending}
                                        onClick={() => {
                                            if (!entry) return;
                                            setDeleteError('');
                                            setShowDeleteDialog(true);
                                        }}
                                    >
                                        <span className="flex items-center gap-2">
                                            <Trash2 className="h-4 w-4" aria-hidden="true" />
                                            {t('knowledgeContent.delete')}
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
                            <ErrorMessage message={deleteError} />
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
                    {showToc ? (
                        <aside className="hidden xl:block">
                            <div
                                className="rounded-2xl bg-[color:var(--color-surface)]/70 p-4 xl:fixed xl:top-40 xl:w-64"
                                style={{
                                    left: 'max(1rem, calc(50% - 36rem - 17rem))',
                                }}
                            >
                                <div className="mb-3 text-[11px] font-semibold uppercase tracking-[0.12em] text-[color:var(--color-text)]">
                                    {t('knowledgeContent.tocTitle')}
                                </div>
                                <nav
                                    className="space-y-2"
                                    aria-label={t('knowledgeContent.tocTitle')}
                                >
                                    {headings.map((heading) => (
                                        <a
                                            key={heading.id}
                                            href={`#${heading.id}`}
                                            onClick={(event) => {
                                                event.preventDefault();
                                                handleHeadingClick(heading.id);
                                            }}
                                            className={[
                                                'block text-sm text-muted transition hover:text-[color:var(--color-text)]',
                                                heading.level === 1 && 'text-[13px] font-semibold',
                                                heading.level === 2 && 'pl-3 text-[12px]',
                                                heading.level === 3 && 'pl-6 text-[11px]',
                                            ]
                                                .filter(Boolean)
                                                .join(' ')}
                                        >
                                            {heading.text}
                                        </a>
                                    ))}
                                </nav>
                            </div>
                        </aside>
                    ) : null}
                </>
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
            <ConfirmDialog
                open={showDeleteDialog}
                title={t('knowledgeContent.deleteTitle')}
                description={t('knowledgeContent.deleteDescription')}
                confirmLabel={t('knowledgeContent.deleteConfirmButton')}
                cancelLabel={t('knowledgeContent.cancelButton')}
                onConfirm={() => {
                    if (!entry || isDeletePending) return;
                    deleteKnowledge({ knowledgeId: entry.id });
                }}
                onClose={() => setShowDeleteDialog(false)}
                isPending={isDeletePending}
            />
        </div>
    );
}

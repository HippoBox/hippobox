import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { ArrowLeft, BookPlus, ChevronDown, Eye, PencilLine, Save } from 'lucide-react';
import { Link, useNavigate, useParams } from 'react-router-dom';

import { Button } from '../components/Button';
import { Card } from '../components/Card';
import { Dropdown } from '../components/Dropdown';
import { ErrorMessage } from '../components/ErrorMessage';
import { Input } from '../components/Input';
import { MarkdownContent } from '../components/MarkdownContent';
import { useKnowledgeList } from '../contexts/KnowledgeListContext';
import {
    useCreateKnowledgeMutation,
    useKnowledgeQuery,
    useUpdateKnowledgeMutation,
} from '../hooks/useKnowledge';
import { useCreateTopicMutation, useTopicsQuery } from '../hooks/useTopics';

const normalizeTags = (raw: string) =>
    Array.from(
        new Set(
            raw
                .split(',')
                .map((tag) => tag.trim())
                .filter(Boolean)
                .map((tag) => tag.replace(/^#/, '')),
        ),
    );

const extractServiceError = (error: unknown) => {
    if (!error || typeof error !== 'object') return {};
    const payload = error as { error?: unknown; message?: unknown; detail?: unknown };
    if (payload.detail && typeof payload.detail === 'object') {
        const detail = payload.detail as { error?: unknown; message?: unknown };
        return {
            code: typeof detail.error === 'string' ? detail.error : undefined,
            message: typeof detail.message === 'string' ? detail.message : undefined,
        };
    }
    return {
        code: typeof payload.error === 'string' ? payload.error : undefined,
        message: typeof payload.message === 'string' ? payload.message : undefined,
    };
};

const extractErrorMessage = (error: unknown, fallback: string) => {
    if (!error) return fallback;
    if (typeof error === 'string') return error;
    if (error instanceof Error && error.message) return error.message;
    if (typeof error === 'object') {
        const payload = error as {
            message?: unknown;
            detail?: unknown;
        };
        if (typeof payload.message === 'string') return payload.message;
        if (typeof payload.detail === 'string') return payload.detail;
        if (payload.detail && typeof payload.detail === 'object') {
            const detail = payload.detail as { message?: unknown };
            if (typeof detail.message === 'string') return detail.message;
        }
    }
    return fallback;
};

export function KnowledgeEditorPage() {
    const { t } = useTranslation();
    const { knowledgeId } = useParams();
    const navigate = useNavigate();
    const isEditMode = Boolean(knowledgeId);
    const { knowledge = [], isPending, isError } = useKnowledgeList();
    const initializedRef = useRef(false);
    const loadedIdRef = useRef<string | null>(null);
    const loadedRevisionRef = useRef<string | null>(null);
    const isDirtyRef = useRef(false);

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
    const entryRevision = useMemo(() => {
        if (!entry) return null;
        const stamp = entry.updated_at ?? entry.created_at ?? '';
        const tags = entry.tags?.join(',') ?? '';
        const titleText = entry.title ?? '';
        const topicText = entry.topic ?? '';
        const contentText = entry.content ?? '';
        return [entry.id, stamp, titleText, topicText, tags, contentText].join('|');
    }, [entry]);

    const [title, setTitle] = useState('');
    const [topic, setTopic] = useState('');
    const [tags, setTags] = useState('');
    const [content, setContent] = useState('');
    const [formError, setFormError] = useState('');
    const [formSuccess, setFormSuccess] = useState('');
    const [fieldErrors, setFieldErrors] = useState<{
        title?: string;
        content?: string;
    }>({});
    const [isPreview, setIsPreview] = useState(false);
    const contentRef = useRef<HTMLTextAreaElement | null>(null);
    const topicDropdownCloseRef = useRef<null | (() => void)>(null);
    const scrollRestoreRef = useRef<number | null>(null);

    const { data: topics = [], isPending: isTopicsPending } = useTopicsQuery();
    const { mutate: createTopic, isPending: isCreateTopicPending } = useCreateTopicMutation({
        onError: (error) => {
            setFormSuccess('');
            setFormError(extractErrorMessage(error, t('main.newKnowledge.form.topicCreateFailed')));
        },
    });
    const topicOptions = useMemo(() => {
        const unique = new Set<string>();
        topics.forEach((item) => {
            if (item.name?.trim()) {
                unique.add(item.name.trim());
            }
        });
        if (entry?.topic?.trim()) {
            unique.add(entry.topic.trim());
        }
        return Array.from(unique).sort((a, b) => a.localeCompare(b));
    }, [topics, entry]);
    const filteredTopicOptions = useMemo(() => {
        const query = topic.trim().toLowerCase();
        if (!query) return topicOptions;
        return topicOptions.filter((item) => item.toLowerCase().includes(query));
    }, [topic, topicOptions]);
    const normalizedTopicInput = topic.trim();
    const hasExactTopic = topicOptions.some(
        (item) => item.toLowerCase() === normalizedTopicInput.toLowerCase(),
    );
    const canCreateTopic = Boolean(normalizedTopicInput) && !hasExactTopic;

    const handleCreateTopic = (close?: () => void) => {
        if (!canCreateTopic || isCreateTopicPending) return;
        createTopic(
            { name: normalizedTopicInput },
            {
                onSuccess: (created) => {
                    setTopic(created.name);
                    if (formError) setFormError('');
                    if (formSuccess) setFormSuccess('');
                    (close ?? topicDropdownCloseRef.current)?.();
                },
            },
        );
    };

    const normalizedContent = content.replace(/\r\n/g, '\n').replace(/\r/g, '\n');

    useEffect(() => {
        if (isPreview) return;
        const textarea = contentRef.current;
        if (!textarea) return;
        const computed = window.getComputedStyle(textarea);
        const lineHeight = Number.parseFloat(computed.lineHeight);
        const paddingTop = Number.parseFloat(computed.paddingTop);
        const paddingBottom = Number.parseFloat(computed.paddingBottom);
        const lineCount = Math.max(normalizedContent.split('\n').length, 1);
        const safeLineHeight = Number.isFinite(lineHeight) ? lineHeight : 24;
        const baselineHeight = safeLineHeight * lineCount;
        const paddingHeight =
            (Number.isFinite(paddingTop) ? paddingTop : 0) +
            (Number.isFinite(paddingBottom) ? paddingBottom : 0);
        const minHeight = baselineHeight + paddingHeight;
        const buffer = Math.ceil(safeLineHeight);
        textarea.style.height = 'auto';
        const targetHeight = Math.max(textarea.scrollHeight, minHeight) + buffer;
        textarea.style.height = `${targetHeight}px`;
    }, [normalizedContent, isPreview]);

    useEffect(() => {
        setIsPreview(false);
    }, [isEditMode]);

    const togglePreview = useCallback(() => {
        scrollRestoreRef.current = window.scrollY;
        setIsPreview((prev) => !prev);
    }, []);

    useEffect(() => {
        if (scrollRestoreRef.current === null) return;
        const targetScroll = scrollRestoreRef.current;
        scrollRestoreRef.current = null;
        requestAnimationFrame(() => {
            window.scrollTo({ top: targetScroll });
            requestAnimationFrame(() => {
                window.scrollTo({ top: targetScroll });
            });
        });
    }, [isPreview]);

    useEffect(() => {
        const handleKeyDown = (event: KeyboardEvent) => {
            if (!event.ctrlKey && !event.metaKey) return;
            if (event.key !== 'Enter') return;
            event.preventDefault();
            togglePreview();
        };
        window.addEventListener('keydown', handleKeyDown);
        return () => {
            window.removeEventListener('keydown', handleKeyDown);
        };
    }, [togglePreview]);

    const { mutate: createKnowledge, isPending: isCreatePending } = useCreateKnowledgeMutation({
        onSuccess: (created) => {
            setFormSuccess(t('main.newKnowledge.form.success'));
            setFormError('');
            setTitle('');
            setTopic('');
            setTags('');
            setContent('');
            setFieldErrors({});
            if (created?.id) {
                navigate(`/app/knowledge/${created.id}`);
            }
        },
        onError: (error) => {
            const serviceError = extractServiceError(error);
            if (serviceError.code === 'TITLE_EXISTS') {
                setFieldErrors({
                    title: t('main.newKnowledge.form.titleDuplicate'),
                });
                setFormError('');
                return;
            }
            setFormSuccess('');
            setFormError(extractErrorMessage(error, t('main.newKnowledge.form.saveFailed')));
        },
    });

    const { mutate: updateKnowledge, isPending: isUpdatePending } = useUpdateKnowledgeMutation({
        onSuccess: () => {
            setFormSuccess(t('knowledgeEditor.form.success'));
            setFormError('');
            setFieldErrors({});
            if (knowledgeId) {
                navigate(`/app/knowledge/${knowledgeId}`);
            }
        },
        onError: (error) => {
            const serviceError = extractServiceError(error);
            if (serviceError.code === 'TITLE_EXISTS') {
                setFieldErrors({
                    title: t('main.newKnowledge.form.titleDuplicate'),
                });
                setFormError('');
                return;
            }
            setFormSuccess('');
            setFormError(extractErrorMessage(error, t('knowledgeEditor.form.saveFailed')));
        },
    });

    useEffect(() => {
        initializedRef.current = false;
        loadedIdRef.current = knowledgeId ?? null;
        setTitle('');
        setTopic('');
        setTags('');
        setContent('');
        setFormError('');
        setFormSuccess('');
        setFieldErrors({});
        loadedRevisionRef.current = null;
        isDirtyRef.current = false;
    }, [knowledgeId]);

    useEffect(() => {
        if (!isEditMode) {
            initializedRef.current = false;
            return;
        }
        if (!entry) return;
        if (loadedIdRef.current && String(entry.id) !== String(loadedIdRef.current)) {
            return;
        }
        const revisionChanged = entryRevision && loadedRevisionRef.current !== entryRevision;
        const shouldInit = !initializedRef.current || (!isDirtyRef.current && revisionChanged);
        if (!shouldInit) return;
        setTitle(entry.title ?? '');
        setTopic(entry.topic ?? '');
        setTags((entry.tags ?? []).join(', '));
        setContent(entry.content ?? '');
        setFieldErrors({});
        initializedRef.current = true;
        loadedRevisionRef.current = entryRevision;
        isDirtyRef.current = false;
    }, [entry, entryRevision, isEditMode]);

    const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        const trimmedTitle = title.trim();
        const trimmedContent = content.trim();
        if (!trimmedTitle || !trimmedContent) {
            setFieldErrors({
                title: trimmedTitle ? undefined : t('main.newKnowledge.form.titleRequired'),
                content: trimmedContent ? undefined : t('main.newKnowledge.form.contentRequired'),
            });
            return;
        }

        const duplicateTitle = knowledge.some((item) => {
            if (item.title?.trim() !== trimmedTitle) return false;
            if (!isEditMode) return true;
            if (!knowledgeId) return true;
            return String(item.id) !== String(knowledgeId);
        });
        if (duplicateTitle) {
            setFieldErrors({
                title: t('main.newKnowledge.form.titleDuplicate'),
                content: undefined,
            });
            return;
        }

        setFieldErrors({});
        const parsedTags = normalizeTags(tags);
        const trimmedTopic = topic.trim();
        if (isEditMode) {
            if (!knowledgeId) return;
            updateKnowledge({
                knowledgeId: Number(knowledgeId),
                body: {
                    title: trimmedTitle,
                    topic: trimmedTopic,
                    content: trimmedContent,
                    tags: parsedTags.length ? parsedTags : undefined,
                },
            });
        } else {
            createKnowledge({
                title: trimmedTitle,
                topic: trimmedTopic,
                content: trimmedContent,
                tags: parsedTags.length ? parsedTags : undefined,
            });
        }
    };

    const isLoadingEntry = isEditMode && (isDirectPending || (isPending && !entry));
    const isLoadError = isEditMode && (isDirectError || (isError && !entry));

    if (isLoadingEntry) {
        return (
            <div className="flex min-h-[40vh] items-center justify-center">
                <span className="badge-chip">{t('knowledgeContent.loading')}</span>
            </div>
        );
    }

    if (isLoadError) {
        return (
            <Card className="p-8 text-center border-0 shadow-none bg-transparent">
                <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full border border-[color:var(--color-border)] bg-[color:var(--color-surface)]">
                    <PencilLine className="h-5 w-5 text-muted" aria-hidden="true" />
                </div>
                <h3 className="mt-4 text-lg font-semibold">{t('knowledgeContent.loadFailed')}</h3>
                <p className="mt-2 text-sm text-muted">{t('knowledgeContent.loadFailedHint')}</p>
            </Card>
        );
    }

    if (isEditMode && !entry) {
        return (
            <Card className="p-8 text-center border-0 shadow-none bg-transparent">
                <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full border border-[color:var(--color-border)] bg-[color:var(--color-surface)]">
                    <PencilLine className="h-5 w-5 text-muted" aria-hidden="true" />
                </div>
                <h3 className="mt-4 text-lg font-semibold">
                    {t('knowledgeContent.notFoundTitle')}
                </h3>
                <p className="mt-2 text-sm text-muted">{t('knowledgeContent.notFoundHint')}</p>
            </Card>
        );
    }

    const isBusy = isCreatePending || isUpdatePending;
    const lineCount = Math.max(normalizedContent.split('\n').length, 1);
    const lineNumbers = Array.from({ length: lineCount }, (_, index) => index + 1);

    return (
        <div className="w-full space-y-10">
            <Card className="space-y-4 p-8 bg-transparent backdrop-blur-0 shadow-none border-0">
                <form className="space-y-4" onSubmit={handleSubmit} noValidate>
                    <div className="flex flex-wrap items-start justify-between gap-4">
                        <div className="flex min-w-0 flex-1 flex-wrap items-start gap-4">
                            <div className="min-w-[220px] flex-1">
                                <Input
                                    id="note-title"
                                    placeholder={t('main.newKnowledge.form.titlePlaceholder')}
                                    className="input-field--borderless"
                                    value={title}
                                    onChange={(event) => {
                                        setTitle(event.target.value);
                                        isDirtyRef.current = true;
                                        if (formError) setFormError('');
                                        if (formSuccess) setFormSuccess('');
                                        if (fieldErrors.title) {
                                            setFieldErrors((prev) => ({
                                                ...prev,
                                                title: undefined,
                                            }));
                                        }
                                    }}
                                />
                                <ErrorMessage message={fieldErrors.title} className="mt-2" />
                            </div>
                            <div className="min-w-[180px]">
                                <Dropdown
                                    side="bottom"
                                    align="start"
                                    offsetY={8}
                                    menuClassName="w-full max-h-64 overflow-auto scrollbar-theme scrollbar-pad"
                                    trigger={({ isOpen, open, toggle }) => (
                                        <div className="relative">
                                            <input
                                                id="note-topic"
                                                className="input-field input-field--borderless pr-10"
                                                placeholder={t(
                                                    'main.newKnowledge.form.topicPlaceholder',
                                                )}
                                                autoComplete="off"
                                                autoCorrect="off"
                                                autoCapitalize="none"
                                                spellCheck={false}
                                                value={topic}
                                                onFocus={open}
                                                onClick={open}
                                                onKeyDown={(event) => {
                                                    if (event.key !== 'Enter') return;
                                                    if (!canCreateTopic) return;
                                                    event.preventDefault();
                                                    handleCreateTopic();
                                                }}
                                                onChange={(event) => {
                                                    setTopic(event.target.value);
                                                    isDirtyRef.current = true;
                                                    open();
                                                    if (formError) setFormError('');
                                                    if (formSuccess) setFormSuccess('');
                                                }}
                                            />
                                            <button
                                                type="button"
                                                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted"
                                                onClick={toggle}
                                                aria-label={t(
                                                    'main.newKnowledge.form.topicPlaceholder',
                                                )}
                                            >
                                                <ChevronDown
                                                    className={`h-4 w-4 transition ${
                                                        isOpen ? 'rotate-180' : ''
                                                    }`}
                                                    aria-hidden="true"
                                                />
                                            </button>
                                        </div>
                                    )}
                                >
                                    {({ close }) => (
                                        <>
                                            {(() => {
                                                topicDropdownCloseRef.current = close;
                                                return null;
                                            })()}
                                            {isTopicsPending ? (
                                                <div className="px-3 py-2 text-xs text-muted">
                                                    {t('main.newKnowledge.form.topicLoading')}
                                                </div>
                                            ) : filteredTopicOptions.length ? (
                                                filteredTopicOptions.map((item) => (
                                                    <button
                                                        key={`topic-${item}`}
                                                        type="button"
                                                        className="menu-item flex w-full items-center rounded-xl px-3 py-2 text-sm font-semibold"
                                                        onClick={() => {
                                                            setTopic(item);
                                                            isDirtyRef.current = true;
                                                            if (formError) setFormError('');
                                                            if (formSuccess) setFormSuccess('');
                                                            close();
                                                        }}
                                                    >
                                                        {item}
                                                    </button>
                                                ))
                                            ) : (
                                                <div className="px-3 py-2 text-xs text-muted">
                                                    {t('main.newKnowledge.form.topicEmpty')}
                                                </div>
                                            )}
                                            {canCreateTopic ? (
                                                <button
                                                    type="button"
                                                    className="menu-item flex w-full items-center rounded-xl px-3 py-2 text-sm font-semibold"
                                                    disabled={isCreateTopicPending}
                                                    onClick={() => {
                                                        handleCreateTopic(close);
                                                    }}
                                                >
                                                    {isCreateTopicPending
                                                        ? t('main.newKnowledge.form.topicCreating')
                                                        : t('main.newKnowledge.form.topicCreate', {
                                                              topic: normalizedTopicInput,
                                                          })}
                                                </button>
                                            ) : null}
                                        </>
                                    )}
                                </Dropdown>
                            </div>
                        </div>
                        <div className="flex shrink-0 items-center gap-2">
                            <Button type="submit" className="h-10 px-4 text-xs" disabled={isBusy}>
                                <span className="flex items-center gap-2">
                                    {isEditMode ? (
                                        <Save className="h-4 w-4" aria-hidden="true" />
                                    ) : (
                                        <BookPlus className="h-4 w-4" aria-hidden="true" />
                                    )}
                                    {isBusy
                                        ? isEditMode
                                            ? t('knowledgeEditor.form.savingButton')
                                            : t('main.newKnowledge.form.savingButton')
                                        : isEditMode
                                          ? t('knowledgeEditor.form.saveButton')
                                          : t('main.newKnowledge.form.saveButton')}
                                </span>
                            </Button>
                            {isEditMode ? (
                                <Link
                                    to={entry ? `/app/knowledge/${entry.id}` : '/app'}
                                    className="shrink-0"
                                >
                                    <Button
                                        type="button"
                                        variant="outline"
                                        className="h-10 px-4 text-xs"
                                    >
                                        <span className="flex items-center gap-2">
                                            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
                                            {t('knowledgeEditor.back')}
                                        </span>
                                    </Button>
                                </Link>
                            ) : null}
                        </div>
                    </div>
                    <Input
                        id="note-tags"
                        placeholder={t('main.newKnowledge.form.tagsPlaceholder')}
                        className="input-field--borderless"
                        value={tags}
                        onChange={(event) => {
                            setTags(event.target.value);
                            isDirtyRef.current = true;
                            if (formError) setFormError('');
                            if (formSuccess) setFormSuccess('');
                        }}
                    />
                    <div className="space-y-2">
                        <div className="flex flex-wrap items-center justify-between gap-3">
                            <label
                                htmlFor="note-content"
                                className="text-xs font-semibold uppercase tracking-[0.25em] text-muted"
                            >
                                {t('main.newKnowledge.form.contentLabel')}
                            </label>
                            <div className="flex items-center gap-3">
                                <span className="text-[10px] text-muted">
                                    Cmd+Enter / Ctrl+Enter
                                </span>
                                <Button
                                    type="button"
                                    variant="outline"
                                    className="h-8 px-3 text-[10px]"
                                    onClick={togglePreview}
                                >
                                    <span className="flex items-center gap-2">
                                        {isPreview ? (
                                            <PencilLine className="h-3 w-3" aria-hidden="true" />
                                        ) : (
                                            <Eye className="h-3 w-3" aria-hidden="true" />
                                        )}
                                        {isPreview
                                            ? t('main.newKnowledge.form.editButton')
                                            : t('main.newKnowledge.form.previewButton')}
                                    </span>
                                </Button>
                            </div>
                        </div>
                        {isPreview ? (
                            <div className="input-field input-field--ghost input-field--borderless min-h-[240px]">
                                {content.trim() ? (
                                    <MarkdownContent content={content} />
                                ) : (
                                    <p className="text-sm text-muted">
                                        {t('main.newKnowledge.form.previewEmpty')}
                                    </p>
                                )}
                            </div>
                        ) : (
                            <div className="editor-grid">
                                <div className="editor-gutter">
                                    {lineNumbers.map((line) => (
                                        <span key={`edit-line-${line}`}>{line}</span>
                                    ))}
                                </div>
                                <textarea
                                    id="note-content"
                                    className="input-field input-field--ghost input-field--expand input-field--borderless editor-textarea min-h-[240px]"
                                    placeholder={t('main.newKnowledge.form.contentPlaceholder')}
                                    value={content}
                                    ref={contentRef}
                                    onChange={(event) => {
                                        setContent(event.target.value);
                                        isDirtyRef.current = true;
                                        if (formError) setFormError('');
                                        if (formSuccess) setFormSuccess('');
                                        if (fieldErrors.content) {
                                            setFieldErrors((prev) => ({
                                                ...prev,
                                                content: undefined,
                                            }));
                                        }
                                    }}
                                />
                            </div>
                        )}
                        <ErrorMessage message={fieldErrors.content} className="mt-2" />
                    </div>

                    <ErrorMessage message={formError} />
                    {formSuccess ? (
                        <p className="rounded-md border border-emerald-500/20 bg-emerald-500/10 px-3 py-2 text-xs text-emerald-600">
                            {formSuccess}
                        </p>
                    ) : null}
                </form>
            </Card>
        </div>
    );
}

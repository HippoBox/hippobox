import { useMemo, useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { BookPlus } from 'lucide-react';
import { BookOpen, ClipboardList, Lightbulb, Sparkles } from 'lucide-react';

import { Button } from '../components/Button';
import { Card } from '../components/Card';
import { ErrorMessage } from '../components/ErrorMessage';
import { Input } from '../components/Input';
import { useCreateKnowledgeMutation } from '../hooks/useKnowledge';

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

const extractErrorMessage = (error: unknown, fallback: string) => {
    if (!error) return fallback;
    if (typeof error === 'string') return error;
    if (error instanceof Error && error.message) return error.message;
    if (typeof error === 'object') {
        const payload = error as { message?: unknown; detail?: unknown };
        if (typeof payload.message === 'string') return payload.message;
        if (typeof payload.detail === 'string') return payload.detail;
    }
    return fallback;
};

export function NewKnowledgePage() {
    const { t } = useTranslation();
    const [title, setTitle] = useState('');
    const [topic, setTopic] = useState('');
    const [tags, setTags] = useState('');
    const [content, setContent] = useState('');
    const [formError, setFormError] = useState('');
    const [formSuccess, setFormSuccess] = useState('');

    const { mutate: createKnowledge, isPending } = useCreateKnowledgeMutation({
        onSuccess: () => {
            setFormSuccess(t('main.newKnowledge.form.success'));
            setFormError('');
            setTitle('');
            setTopic('');
            setTags('');
            setContent('');
        },
        onError: (error) => {
            setFormSuccess('');
            setFormError(extractErrorMessage(error, t('main.newKnowledge.form.saveFailed')));
        },
    });

    const tips = useMemo(
        () => [
            t('main.newKnowledge.tips.item1'),
            t('main.newKnowledge.tips.item2'),
            t('main.newKnowledge.tips.item3'),
        ],
        [t],
    );

    const templates = useMemo(
        () => [
            {
                title: t('main.newKnowledge.templates.meeting'),
                description: t('main.newKnowledge.templates.meetingHint'),
                icon: ClipboardList,
            },
            {
                title: t('main.newKnowledge.templates.reading'),
                description: t('main.newKnowledge.templates.readingHint'),
                icon: BookOpen,
            },
            {
                title: t('main.newKnowledge.templates.idea'),
                description: t('main.newKnowledge.templates.ideaHint'),
                icon: Lightbulb,
            },
        ],
        [t],
    );

    const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        const trimmedTitle = title.trim();
        const trimmedTopic = topic.trim();
        const trimmedContent = content.trim();
        if (!trimmedTitle || !trimmedTopic || !trimmedContent) {
            setFormError(t('main.newKnowledge.form.requiredError'));
            setFormSuccess('');
            return;
        }

        const parsedTags = normalizeTags(tags);
        createKnowledge({
            title: trimmedTitle,
            topic: trimmedTopic,
            content: trimmedContent,
            tags: parsedTags.length ? parsedTags : undefined,
        });
    };

    const handleClear = () => {
        setTitle('');
        setTopic('');
        setTags('');
        setContent('');
        setFormError('');
        setFormSuccess('');
    };

    return (
        <div className="w-full space-y-10">
            <div className="space-y-1">
                <div className="flex items-center gap-3">
                    <BookPlus className="h-5 w-5 text-muted" aria-hidden="true" />
                    <h2 className="font-display text-2xl font-semibold">
                        {t('main.newKnowledge.title')}
                    </h2>
                </div>
                <p className="max-w-2xl text-sm text-muted sm:text-base">
                    {t('main.newKnowledge.subtitle')}
                </p>
            </div>

            <div className="grid gap-6 lg:grid-cols-[minmax(0,1.55fr)_minmax(0,1fr)]">
                <Card className="animate-fade-up p-8" variant="strong">
                    <form className="space-y-6" onSubmit={handleSubmit}>
                        <div className="grid gap-4 md:grid-cols-2">
                            <Input
                                id="note-title"
                                label={t('main.newKnowledge.form.titleLabel')}
                                placeholder={t('main.newKnowledge.form.titlePlaceholder')}
                                value={title}
                                onChange={(event) => {
                                    setTitle(event.target.value);
                                    if (formError) setFormError('');
                                    if (formSuccess) setFormSuccess('');
                                }}
                                required
                            />
                            <Input
                                id="note-topic"
                                label={t('main.newKnowledge.form.topicLabel')}
                                placeholder={t('main.newKnowledge.form.topicPlaceholder')}
                                value={topic}
                                onChange={(event) => {
                                    setTopic(event.target.value);
                                    if (formError) setFormError('');
                                    if (formSuccess) setFormSuccess('');
                                }}
                                required
                            />
                        </div>
                        <Input
                            id="note-tags"
                            label={t('main.newKnowledge.form.tagsLabel')}
                            placeholder={t('main.newKnowledge.form.tagsPlaceholder')}
                            value={tags}
                            onChange={(event) => {
                                setTags(event.target.value);
                                if (formError) setFormError('');
                                if (formSuccess) setFormSuccess('');
                            }}
                        />
                        <div className="space-y-2">
                            <label
                                htmlFor="note-content"
                                className="text-xs font-semibold uppercase tracking-[0.25em] text-muted"
                            >
                                {t('main.newKnowledge.form.contentLabel')}
                            </label>
                            <textarea
                                id="note-content"
                                className="input-field min-h-[240px] resize-y"
                                placeholder={t('main.newKnowledge.form.contentPlaceholder')}
                                value={content}
                                onChange={(event) => {
                                    setContent(event.target.value);
                                    if (formError) setFormError('');
                                    if (formSuccess) setFormSuccess('');
                                }}
                                required
                            />
                            <p className="text-xs text-muted">
                                {t('main.newKnowledge.form.contentHint')}
                            </p>
                        </div>

                        <ErrorMessage message={formError} />
                        {formSuccess ? (
                            <p className="rounded-md border border-emerald-500/20 bg-emerald-500/10 px-3 py-2 text-xs text-emerald-600">
                                {formSuccess}
                            </p>
                        ) : null}

                        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                            <Button type="button" variant="outline" onClick={handleClear}>
                                {t('main.newKnowledge.form.clearButton')}
                            </Button>
                            <Button type="submit" disabled={isPending}>
                                {isPending
                                    ? t('main.newKnowledge.form.savingButton')
                                    : t('main.newKnowledge.form.saveButton')}
                            </Button>
                        </div>
                    </form>
                </Card>

                <div className="space-y-6">
                    <Card className="p-6">
                        <div className="flex items-center gap-2">
                            <Sparkles className="h-4 w-4 text-muted" aria-hidden="true" />
                            <h2 className="text-sm font-semibold">
                                {t('main.newKnowledge.tips.title')}
                            </h2>
                        </div>
                        <ul className="mt-4 space-y-3 text-sm text-muted">
                            {tips.map((tip) => (
                                <li key={tip} className="flex gap-3">
                                    <span className="mt-2 h-2 w-2 rounded-full bg-[color:var(--color-accent)]" />
                                    <span>{tip}</span>
                                </li>
                            ))}
                        </ul>
                    </Card>

                    <Card className="p-6">
                        <div className="flex items-center gap-2">
                            <BookOpen className="h-4 w-4 text-muted" aria-hidden="true" />
                            <h2 className="text-sm font-semibold">
                                {t('main.newKnowledge.templates.title')}
                            </h2>
                        </div>
                        <div className="mt-4 space-y-3">
                            {templates.map((template) => (
                                <div
                                    key={template.title}
                                    className="flex items-start gap-3 rounded-2xl border border-[color:var(--color-border)] bg-[color:var(--color-surface)]/70 px-4 py-3"
                                >
                                    <template.icon
                                        className="mt-0.5 h-4 w-4 text-muted"
                                        aria-hidden="true"
                                    />
                                    <div>
                                        <div className="text-sm font-semibold">
                                            {template.title}
                                        </div>
                                        <div className="text-xs text-muted">
                                            {template.description}
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </Card>
                </div>
            </div>
        </div>
    );
}

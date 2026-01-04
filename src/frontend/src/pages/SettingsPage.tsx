import type { ChangeEvent } from 'react';
import { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useLocation, useNavigate } from 'react-router-dom';
import {
    ChevronDown,
    Globe,
    Key,
    Moon,
    Palette,
    Settings,
    SlidersHorizontal,
    Sun,
    Check,
    Copy,
    Trash2,
    User,
} from 'lucide-react';

import { Button } from '../components/Button';
import { Card } from '../components/Card';
import { ConfirmDialog } from '../components/ConfirmDialog';
import { ErrorMessage } from '../components/ErrorMessage';
import { Input } from '../components/Input';
import { useMeQuery, useUpdateProfileMutation } from '../hooks/useAuth';
import {
    useApiKeysQuery,
    useCreateApiKeyMutation,
    useDeleteApiKeyMutation,
    useUpdateApiKeyMutation,
    type ApiKeyCreatedResponse,
} from '../hooks/useApiKeys';
import { ToggleButton } from '../components/ToggleButton';
import { useTheme } from '../context/ThemeContext';
import { supportedLanguages, type Language } from '../i18n';

type SettingsTab = 'profile' | 'general' | 'apiKey';

export function SettingsPage() {
    const { t, i18n } = useTranslation();
    const location = useLocation();
    const navigate = useNavigate();
    const { data: me } = useMeQuery();
    const [name, setName] = useState('');
    const [nameError, setNameError] = useState<string | null>(null);
    const [apiKeyName, setApiKeyName] = useState('');
    const [apiKeyError, setApiKeyError] = useState<string | null>(null);
    const [createdKey, setCreatedKey] = useState<ApiKeyCreatedResponse | null>(null);
    const [showSecretModal, setShowSecretModal] = useState(false);
    const [copiedSecret, setCopiedSecret] = useState(false);
    const [deleteTarget, setDeleteTarget] = useState<{ id: number; name: string } | null>(null);
    const { mutate: updateProfile, isPending: isSaving } = useUpdateProfileMutation({
        onSuccess: () => setNameError(null),
        onError: (error) => {
            const fallback = t('settings.profile.saveFailed');
            if (!error || typeof error !== 'object') {
                setNameError(fallback);
                return;
            }
            const payload = error as { error?: string; message?: string };
            if (payload.error === 'NAME_ALREADY_EXISTS') {
                setNameError(t('settings.profile.nameDuplicate'));
                return;
            }
            setNameError(payload.message ?? fallback);
        },
    });
    const { theme, toggleTheme } = useTheme();

    const tabs = useMemo(
        () => [
            {
                id: 'profile' as const,
                label: t('settings.sections.profile'),
                icon: <User className="h-4 w-4 text-muted" aria-hidden="true" />,
            },
            {
                id: 'general' as const,
                label: t('settings.sections.general'),
                icon: <SlidersHorizontal className="h-4 w-4 text-muted" aria-hidden="true" />,
            },
            {
                id: 'apiKey' as const,
                label: t('settings.sections.apiKey'),
                icon: <Key className="h-4 w-4 text-muted" aria-hidden="true" />,
            },
        ],
        [t],
    );

    const activeTab = useMemo(() => {
        const hash = location.hash.replace('#', '');
        if (hash === 'profile' || hash === 'general' || hash === 'apiKey') {
            return hash;
        }
        return 'profile';
    }, [location.hash]);

    const activeTabConfig = tabs.find((tab) => tab.id === activeTab);
    const activeLabel = activeTabConfig?.label ?? t('settings.sections.profile');
    const activeIcon = activeTabConfig?.icon;
    const {
        data: apiKeys,
        isLoading: isApiKeysLoading,
        isError: isApiKeysError,
    } = useApiKeysQuery({ enabled: activeTab === 'apiKey' });
    const { mutate: createApiKey, isPending: isCreatingApiKey } = useCreateApiKeyMutation({
        onSuccess: (data) => {
            setCreatedKey(data);
            setApiKeyName('');
            setApiKeyError(null);
            setCopiedSecret(false);
            setShowSecretModal(true);
        },
        onError: (error) => {
            const fallback = t('settings.apiKey.createFailed');
            if (!error || typeof error !== 'object') {
                setApiKeyError(fallback);
                return;
            }
            const payload = error as { error?: string; message?: string };
            setApiKeyError(payload.message ?? fallback);
        },
    });
    const { mutate: deleteApiKey, isPending: isDeletingApiKey } = useDeleteApiKeyMutation({
        onError: () => {
            setApiKeyError(t('settings.apiKey.deleteFailed'));
        },
    });
    const { mutate: updateApiKey, isPending: isUpdatingApiKey } = useUpdateApiKeyMutation({
        onError: () => {
            setApiKeyError(t('settings.apiKey.updateFailed'));
        },
    });

    useEffect(() => {
        const nextName = (me as { name?: unknown } | undefined)?.name;
        if (typeof nextName === 'string' && nextName.trim()) {
            setName(nextName);
        }
    }, [me]);

    useEffect(() => {
        if (nameError) {
            setNameError(null);
        }
    }, [name]);

    useEffect(() => {
        if (apiKeyError) {
            setApiKeyError(null);
        }
    }, [apiKeyName]);

    useEffect(() => {
        if (!location.hash) {
            navigate({ hash: 'profile' }, { replace: true });
        }
    }, [location.hash, navigate]);

    const handleTabChange = (tab: SettingsTab) => {
        if (tab === activeTab) return;
        navigate({ hash: tab }, { replace: true });
    };

    const profileEmail = (me as { email?: unknown } | undefined)?.email;
    const resolvedEmail = typeof profileEmail === 'string' ? profileEmail : '';
    const profileInitial = useMemo(() => {
        const source = name || (me as { name?: string } | undefined)?.name || 'H';
        const [initial] = Array.from(source.trim());
        return initial ? initial.toUpperCase() : 'H';
    }, [name, me]);
    const avatarUrl = (me as { avatar_url?: unknown } | undefined)?.avatar_url;
    const resolvedAvatarUrl =
        typeof avatarUrl === 'string' && avatarUrl.trim() ? avatarUrl : undefined;

    const handleProfileSave = () => {
        const trimmed = name.trim();
        if (!trimmed) {
            setNameError(t('settings.profile.nameRequired'));
            return;
        }
        updateProfile({ name: trimmed });
    };

    const handleApiKeyCreate = () => {
        const trimmed = apiKeyName.trim();
        if (!trimmed) {
            setApiKeyError(t('settings.apiKey.nameRequired'));
            return;
        }
        createApiKey(trimmed);
    };

    const handleCopySecret = async (secret: string) => {
        if (!secret) return;
        try {
            await navigator.clipboard.writeText(secret);
            setCopiedSecret(true);
            window.setTimeout(() => setCopiedSecret(false), 1600);
        } catch {
            setCopiedSecret(false);
        }
    };

    const handleCloseSecretModal = () => {
        setShowSecretModal(false);
    };

    const handleToggleApiKey = (keyId: number, nextActive: boolean) => {
        updateApiKey({ keyId, is_active: nextActive });
    };

    const handleDeleteApiKey = (keyId: number, name: string) => {
        setDeleteTarget({ id: keyId, name });
    };

    const handleCloseDeleteDialog = () => {
        if (isDeletingApiKey) return;
        setDeleteTarget(null);
    };

    const handleConfirmDelete = () => {
        if (!deleteTarget) return;
        deleteApiKey(deleteTarget.id, {
            onSettled: () => setDeleteTarget(null),
        });
    };

    const formatDate = (value: string | null) => {
        if (!value) return '-';
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) return '-';
        return date.toLocaleDateString();
    };

    const activeLanguage = supportedLanguages.includes(i18n.language as Language)
        ? (i18n.language as Language)
        : 'en';

    const handleLanguageChange = (event: ChangeEvent<HTMLSelectElement>) => {
        const nextLanguage = event.target.value as Language;
        if (!supportedLanguages.includes(nextLanguage)) return;
        void i18n.changeLanguage(nextLanguage);
        try {
            window.localStorage.setItem('lang', nextLanguage);
        } catch {
            // ignore storage errors
        }
    };

    return (
        <div className="w-full space-y-6">
            <div className="space-y-1">
                <div className="flex items-center gap-3">
                    <Settings className="h-5 w-5 text-muted" aria-hidden="true" />
                    <h2 className="font-display text-2xl font-semibold">{t('settings.title')}</h2>
                </div>
            </div>
            <div className="flex flex-col gap-4 lg:flex-row">
                <Card className="w-full p-4 lg:w-64 lg:self-start lg:h-fit">
                    <nav className="space-y-2">
                        {tabs.map((tab) => (
                            <button
                                key={tab.id}
                                type="button"
                                onClick={() => handleTabChange(tab.id)}
                                className={`flex w-full items-center justify-between rounded-xl px-3 py-2 text-sm font-semibold transition ${
                                    activeTab === tab.id
                                        ? 'bg-[color:var(--color-text)] text-[color:var(--color-primary-contrast)]'
                                        : 'text-[color:var(--color-text)] hover:bg-black/5'
                                }`}
                            >
                                <span className="flex items-center gap-2">
                                    {tab.icon}
                                    {tab.label}
                                </span>
                            </button>
                        ))}
                    </nav>
                </Card>
                <Card className="flex-1 p-6">
                    <div className="space-y-2">
                        <h3 className="flex items-center gap-2 font-display text-xl font-semibold">
                            {activeIcon}
                            {activeLabel}
                        </h3>
                        {activeTab === 'profile' ? (
                            <p className="text-sm text-muted">{t('settings.profile.subtitle')}</p>
                        ) : null}
                    </div>
                    {activeTab === 'profile' ? (
                        <div className="mt-6 space-y-6">
                            <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between">
                                <div className="w-full space-y-4 sm:max-w-sm">
                                    <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
                                        <Input
                                            id="settings-profile-name"
                                            label={t('settings.profile.nameLabel')}
                                            placeholder={t('common.fields.namePlaceholder')}
                                            value={name}
                                            onChange={(event) => setName(event.target.value)}
                                            className="w-full"
                                        />
                                        <Button
                                            type="button"
                                            className="shrink-0"
                                            onClick={handleProfileSave}
                                            disabled={isSaving}
                                        >
                                            {t('settings.profile.saveButton')}
                                        </Button>
                                    </div>
                                    <ErrorMessage message={nameError} />
                                    <div className="space-y-1">
                                        <div className="text-xs font-semibold text-muted">
                                            {t('settings.profile.emailLabel')}
                                        </div>
                                        <div className="text-sm text-[color:var(--color-text)]">
                                            {resolvedEmail || '-'}
                                        </div>
                                    </div>
                                </div>
                                <div className="flex h-40 w-40 items-center justify-center overflow-hidden rounded-full border border-[color:var(--color-border-strong)] bg-[color:var(--color-surface)] font-display text-lg font-semibold text-[color:var(--color-text)] shadow-[0_10px_24px_rgba(15,23,42,0.12)] self-start sm:ml-6 sm:-mt-4">
                                    {resolvedAvatarUrl ? (
                                        <img
                                            src={resolvedAvatarUrl}
                                            alt=""
                                            className="h-full w-full object-cover"
                                        />
                                    ) : (
                                        <span aria-hidden="true">{profileInitial}</span>
                                    )}
                                </div>
                            </div>
                        </div>
                    ) : null}
                    {activeTab === 'general' ? (
                        <div className="mt-6 space-y-6">
                            <div className="space-y-8 max-w-sm">
                                <div className="space-y-2">
                                    <label
                                        htmlFor="settings-language"
                                        className="flex items-center gap-2 text-sm font-semibold uppercase tracking-[0.22em] text-muted"
                                    >
                                        <Globe className="h-3.5 w-3.5" aria-hidden="true" />
                                        {t('settings.general.languageLabel')}
                                    </label>
                                    <div className="relative">
                                        <select
                                            id="settings-language"
                                            className="input-field appearance-none pr-12"
                                            value={activeLanguage}
                                            onChange={handleLanguageChange}
                                        >
                                            <option value="en">
                                                {t('settings.general.languageEnglish')}
                                            </option>
                                            <option value="ko">
                                                {t('settings.general.languageKorean')}
                                            </option>
                                        </select>
                                        <ChevronDown
                                            className="pointer-events-none absolute right-4 top-1/2 h-4 w-4 -translate-y-1/2 text-muted"
                                            aria-hidden="true"
                                        />
                                    </div>
                                    <p className="text-xs text-muted">
                                        {t('settings.general.languageHint')}
                                    </p>
                                </div>
                                <div className="space-y-2">
                                    <div className="flex items-center gap-2 text-sm font-semibold uppercase tracking-[0.22em] text-muted">
                                        <Palette className="h-3.5 w-3.5" aria-hidden="true" />
                                        {t('settings.general.themeLabel')}
                                    </div>
                                    <div className="flex items-center justify-between rounded-2xl border border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-4 py-3">
                                        <div>
                                            <div className="flex items-center gap-2 text-sm font-semibold text-[color:var(--color-text)]">
                                                {theme === 'dark' ? (
                                                    <Moon className="h-4 w-4" aria-hidden="true" />
                                                ) : (
                                                    <Sun className="h-4 w-4" aria-hidden="true" />
                                                )}
                                                <span>
                                                    {theme === 'dark'
                                                        ? t('settings.general.themeDark')
                                                        : t('settings.general.themeLight')}
                                                </span>
                                            </div>
                                        </div>
                                        <ToggleButton
                                            checked={theme === 'dark'}
                                            onChange={toggleTheme}
                                            size="sm"
                                            className={
                                                theme === 'light' ? '!bg-slate-900' : undefined
                                            }
                                        />
                                    </div>
                                </div>
                            </div>
                        </div>
                    ) : null}
                    {activeTab === 'apiKey' ? (
                        <div className="mt-6 space-y-6">
                            <div className="space-y-3 max-w-sm">
                                <Input
                                    id="settings-api-key-name"
                                    label={t('settings.apiKey.nameLabel')}
                                    placeholder={t('settings.apiKey.nameLabel')}
                                    value={apiKeyName}
                                    onChange={(event) => setApiKeyName(event.target.value)}
                                />
                                <Button
                                    type="button"
                                    onClick={handleApiKeyCreate}
                                    disabled={isCreatingApiKey}
                                >
                                    {t('settings.apiKey.createButton')}
                                </Button>
                                <ErrorMessage message={apiKeyError} />
                            </div>

                            <div className="space-y-3">
                                <div className="text-sm font-semibold">
                                    {t('settings.apiKey.listTitle')}
                                </div>
                                {isApiKeysLoading ? (
                                    <p className="text-xs text-muted">
                                        {t('settings.apiKey.loading')}
                                    </p>
                                ) : isApiKeysError ? (
                                    <p className="text-xs text-rose-500">
                                        {t('settings.apiKey.loadFailed')}
                                    </p>
                                ) : apiKeys && apiKeys.length > 0 ? (
                                    <div className="space-y-3">
                                        {apiKeys.map((key) => (
                                            <div
                                                key={key.id}
                                                className="rounded-2xl border border-[color:var(--color-border)] bg-[color:var(--color-surface)]/90 p-4"
                                            >
                                                <div className="flex items-center justify-between gap-4">
                                                    <div>
                                                        <div className="text-sm font-semibold">
                                                            {key.name}
                                                        </div>
                                                        <div className="text-xs text-muted">
                                                            {t('settings.apiKey.accessKeyLabel')}{' '}
                                                            {key.access_key}
                                                        </div>
                                                    </div>
                                                    <div className="flex min-w-[160px] items-center justify-end gap-3">
                                                        <span
                                                            className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
                                                                key.is_active
                                                                    ? 'bg-emerald-500/10 text-emerald-600'
                                                                    : 'bg-slate-500/10 text-slate-500'
                                                            }`}
                                                        >
                                                            {key.is_active
                                                                ? t('settings.apiKey.statusActive')
                                                                : t(
                                                                      'settings.apiKey.statusInactive',
                                                                  )}
                                                        </span>
                                                        <ToggleButton
                                                            checked={key.is_active}
                                                            onChange={() =>
                                                                handleToggleApiKey(
                                                                    key.id,
                                                                    !key.is_active,
                                                                )
                                                            }
                                                            size="sm"
                                                            className={
                                                                key.is_active
                                                                    ? undefined
                                                                    : 'opacity-70'
                                                            }
                                                            disabled={isUpdatingApiKey}
                                                        />
                                                    </div>
                                                </div>
                                                <div className="mt-4 flex items-center justify-between gap-4 border-t border-[color:var(--color-border)] pt-3 text-xs text-muted">
                                                    <div className="grid flex-1 gap-2 sm:grid-cols-3 sm:gap-x-6">
                                                        <div>
                                                            {t('settings.apiKey.totalRequests')}:{' '}
                                                            {key.total_requests}
                                                        </div>
                                                        <div>
                                                            {t('settings.apiKey.createdAt')}:{' '}
                                                            {formatDate(key.created_at)}
                                                        </div>
                                                        <div>
                                                            {t('settings.apiKey.lastUsed')}:{' '}
                                                            {formatDate(key.last_used_at)}
                                                        </div>
                                                    </div>
                                                    <div className="flex min-w-[160px] justify-end">
                                                        <button
                                                            type="button"
                                                            onClick={() =>
                                                                handleDeleteApiKey(key.id, key.name)
                                                            }
                                                            disabled={isDeletingApiKey}
                                                            className="inline-flex items-center gap-1.5 rounded-full border border-rose-500/20 px-2.5 py-1 text-xs font-semibold text-rose-500 transition hover:border-rose-500/40 hover:bg-rose-500/10 disabled:opacity-60"
                                                            aria-label={t(
                                                                'settings.apiKey.deleteButton',
                                                            )}
                                                        >
                                                            <Trash2
                                                                className="h-3.5 w-3.5"
                                                                aria-hidden="true"
                                                            />
                                                            <span>
                                                                {t('settings.apiKey.deleteButton')}
                                                            </span>
                                                        </button>
                                                    </div>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                ) : (
                                    <p className="text-xs text-muted">
                                        {t('settings.apiKey.empty')}
                                    </p>
                                )}
                            </div>
                        </div>
                    ) : null}
                </Card>
            </div>
            <ConfirmDialog
                open={!!deleteTarget}
                title={t('settings.apiKey.deleteTitle')}
                description={t('settings.apiKey.deleteDescription')}
                confirmLabel={t('settings.apiKey.deleteConfirmButton')}
                cancelLabel={t('settings.apiKey.cancelButton')}
                onConfirm={handleConfirmDelete}
                onClose={handleCloseDeleteDialog}
                isPending={isDeletingApiKey}
            />
            <ConfirmDialog
                open={showSecretModal && !!createdKey}
                title={t('settings.apiKey.secretTitle')}
                description={t('settings.apiKey.secretHint')}
                cancelLabel={t('settings.apiKey.closeButton')}
                onClose={handleCloseSecretModal}
            >
                {createdKey ? (
                    <div className="flex items-center gap-3 rounded-2xl border border-[color:var(--color-border-strong)] bg-[color:var(--color-surface)]/90 px-3 py-3">
                        <code className="flex-1 break-all text-xs text-[color:var(--color-text)]">
                            {createdKey.secret_key}
                        </code>
                        <button
                            type="button"
                            onClick={() => handleCopySecret(createdKey.secret_key)}
                            className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-[color:var(--color-border)] text-muted transition hover:border-emerald-500/40 hover:bg-emerald-500/10 hover:text-emerald-500"
                            aria-label={t('settings.apiKey.copyButton')}
                        >
                            {copiedSecret ? (
                                <Check className="h-4 w-4" aria-hidden="true" />
                            ) : (
                                <Copy className="h-4 w-4" aria-hidden="true" />
                            )}
                        </button>
                    </div>
                ) : null}
            </ConfirmDialog>
        </div>
    );
}

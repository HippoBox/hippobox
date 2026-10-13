import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { API_ORIGIN } from '../api';
import { authedFetch } from '../api/client';
import { useMeQuery } from '../hooks/useAuth';
import { useEmailEnabled } from '../hooks/useFeatures';
import { Button } from './Button';
import { Input } from './Input';
import { ErrorMessage } from './ErrorMessage';

async function request(path: string, method = 'GET', body?: unknown) {
    const response = await authedFetch(`${API_ORIGIN}/api/v1/${path}`, {
        method,
        headers: body ? { 'Content-Type': 'application/json' } : undefined,
        body: body ? JSON.stringify(body) : undefined,
    });
    if (!response.ok) throw new Error('Account request failed');
    return response.json();
}

type Profile = { bio?: string; role?: string };
type Inbox = { items: { id: number; title: string; body: string; read_at: string | null }[] };
type Directory = { items: { id: number; name: string; role: string; is_active: boolean }[] };

export function PlatformAccountPanel() {
    const { t } = useTranslation();
    const queryClient = useQueryClient();
    const { data: rawProfile } = useMeQuery();
    const profile = rawProfile as Profile | undefined;
    const { emailEnabled } = useEmailEnabled();
    const [bio, setBio] = useState('');
    const [code, setCode] = useState('');
    const [password, setPassword] = useState('');
    useEffect(() => setBio(profile?.bio ?? ''), [profile?.bio]);
    const save = useMutation({
        mutationFn: () => request('auth/me', 'PATCH', { bio: bio || null }),
        onSuccess: () => queryClient.invalidateQueries({ queryKey: ['auth', 'me'] }),
    });
    const sendCode = useMutation({ mutationFn: () => request('auth/me/password/code', 'POST') });
    const changePassword = useMutation({
        mutationFn: () => request('auth/me/password', 'POST', { code, password }),
        onSuccess: () => {
            setCode('');
            setPassword('');
        },
    });
    const inbox = useQuery<Inbox>({
        queryKey: ['account', 'inbox'],
        queryFn: () => request('inbox'),
    });
    const markRead = useMutation({
        mutationFn: (id: number) =>
            request('inbox/read-selected', 'POST', { notification_ids: [id] }),
        onSuccess: () => queryClient.invalidateQueries({ queryKey: ['account', 'inbox'] }),
    });
    const directory = useQuery<Directory>({
        queryKey: ['account', 'directory'],
        queryFn: () => request('auth/admin/users'),
        enabled: profile?.role === 'admin' || profile?.role === 'manager',
    });
    return (
        <div className="space-y-6 border-t border-[color:var(--color-border)] pt-6">
            <section className="space-y-3">
                <Input
                    id="profile-bio"
                    label={t('platform.bio')}
                    value={bio}
                    maxLength={100}
                    onChange={(event) => setBio(event.target.value)}
                />
                <Button
                    type="button"
                    variant="outline"
                    disabled={save.isPending}
                    onClick={() => save.mutate()}
                >
                    {t('platform.saveBio')}
                </Button>
                {save.isSuccess && (
                    <p role="status" className="text-sm text-muted">
                        {t('platform.saved')}
                    </p>
                )}
                <ErrorMessage message={save.isError ? t('platform.failed') : ''} />
            </section>
            <section className="space-y-3">
                <h4 className="font-semibold">{t('platform.security')}</h4>
                {emailEnabled ? (
                    <>
                        <Button
                            type="button"
                            variant="outline"
                            disabled={sendCode.isPending}
                            onClick={() => sendCode.mutate()}
                        >
                            {t('platform.sendCode')}
                        </Button>
                        {sendCode.isSuccess && (
                            <p role="status" className="text-sm text-muted">
                                {t('platform.codeSent')}
                            </p>
                        )}
                        <Input
                            id="password-code"
                            label={t('platform.code')}
                            value={code}
                            inputMode="numeric"
                            maxLength={6}
                            onChange={(event) => setCode(event.target.value)}
                        />
                        <Input
                            id="new-account-password"
                            label={t('platform.newPassword')}
                            type="password"
                            value={password}
                            autoComplete="new-password"
                            onChange={(event) => setPassword(event.target.value)}
                        />
                        <p className="text-xs text-muted">{t('common.errors.invalidPassword')}</p>
                        <Button
                            type="button"
                            disabled={
                                changePassword.isPending || !/^\d{6}$/.test(code) || !password
                            }
                            onClick={() => changePassword.mutate()}
                        >
                            {t('platform.changePassword')}
                        </Button>
                        {changePassword.isSuccess && (
                            <p role="status" className="text-sm text-muted">
                                {t('platform.passwordChanged')}
                            </p>
                        )}
                        <ErrorMessage
                            message={
                                sendCode.isError || changePassword.isError
                                    ? t('platform.failed')
                                    : ''
                            }
                        />
                    </>
                ) : (
                    <p className="text-sm text-muted">{t('platform.emailRequired')}</p>
                )}
            </section>
            <section className="space-y-3">
                <h4 className="font-semibold">{t('platform.inbox')}</h4>
                {inbox.isPending && <p className="text-sm text-muted">{t('platform.loading')}</p>}
                {inbox.data?.items.length === 0 && (
                    <p className="text-sm text-muted">{t('platform.empty')}</p>
                )}
                {inbox.data?.items.map((item) => (
                    <article
                        key={item.id}
                        className="space-y-2 rounded-xl border border-[color:var(--color-border)] p-3"
                    >
                        <p className="text-sm font-medium">{item.title}</p>
                        <p className="text-sm text-muted">{item.body}</p>
                        {!item.read_at && (
                            <Button
                                type="button"
                                variant="outline"
                                disabled={markRead.isPending}
                                onClick={() => markRead.mutate(item.id)}
                            >
                                {t('platform.markRead')}
                            </Button>
                        )}
                    </article>
                ))}
                <ErrorMessage
                    message={inbox.isError || markRead.isError ? t('platform.failed') : ''}
                />
            </section>
            {directory.isEnabled && (
                <section className="space-y-3">
                    <h4 className="font-semibold">{t('platform.members')}</h4>
                    {directory.data?.items.map((user) => (
                        <div key={user.id} className="flex justify-between gap-3 text-sm">
                            <span>{user.name}</span>
                            <span className="text-muted">{user.role}</span>
                        </div>
                    ))}
                    <ErrorMessage message={directory.isError ? t('platform.failed') : ''} />
                </section>
            )}
        </div>
    );
}

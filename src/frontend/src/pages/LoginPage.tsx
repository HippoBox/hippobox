import { useEffect, useMemo, useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useSearchParams } from 'react-router-dom';

import { Button } from '../components/Button';
import { Card } from '../components/Card';
import { Container } from '../components/Container';
import { ErrorMessage } from '../components/ErrorMessage';
import { Input } from '../components/Input';
import { AuthHeader } from '../components/AuthHeader';
import { LoadingPage } from '../pages/LoadingPage';
import {
    useLoginMutation,
    useRefreshTokenMutation,
    useResendVerificationEmailMutation,
} from '../hooks/useAuth';
import { useAccessToken } from '../hooks/useSession';
import { isValidEmail, isValidPassword } from '../utils/validation';

type FormErrorKey = '' | 'requiredEmail' | 'invalidEmail' | 'requiredPassword' | 'invalidPassword';

export function LoginPage() {
    const { t } = useTranslation();
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const token = useAccessToken();
    const [email, setEmail] = useState(() => searchParams.get('email') ?? '');
    const [password, setPassword] = useState('');
    const [rememberMe, setRememberMe] = useState(false);
    const [formErrorKey, setFormErrorKey] = useState<FormErrorKey>('');
    const [resendComplete, setResendComplete] = useState(false);

    const {
        mutate: refreshSession,
        isIdle: isRefreshIdle,
        isPending: isRefreshPending,
    } = useRefreshTokenMutation();

    const loginMutation = useLoginMutation({
        onSuccess: () => {
            navigate('/app');
        },
    });

    const resendMutation = useResendVerificationEmailMutation({
        onSuccess: () => {
            setResendComplete(true);
        },
    });

    const emailNotVerified = useMemo(() => {
        const error = loginMutation.error;
        if (!error || typeof error !== 'object') return false;
        const detail = (error as { detail?: unknown }).detail;
        if (!detail || typeof detail !== 'object') return false;
        return (detail as { error?: unknown }).error === 'EMAIL_NOT_VERIFIED';
    }, [loginMutation.error]);

    const apiErrorMessage = useMemo(() => {
        const error = loginMutation.error;
        if (!error) return '';

        if (typeof error === 'string') {
            return error;
        }

        if (error instanceof Error && error.message) {
            return error.message;
        }

        if (typeof error === 'object') {
            const detail = (error as { detail?: unknown }).detail;
            if (detail && typeof detail === 'object') {
                const code = (detail as { error?: unknown }).error;
                const message = (detail as { message?: unknown }).message;
                if (code === 'EMAIL_NOT_VERIFIED') return t('login.verifyRequired');

                if (code === `INVALID_CREDENTIALS`) {
                    const limit_count = (detail as { limit_count?: unknown }).limit_count;
                    return t('login.invalidCredentials', { limit_count: limit_count });
                }

                if (code === `ACCOUNT_LOCKED`) {
                    const remaining_seconds = (detail as { remaining_seconds?: unknown })
                        .remaining_seconds;
                    return t('login.accountLocked', { remaining_seconds: remaining_seconds });
                }

                if (typeof message === 'string' && message) return message;
            }
        }

        return t('login.errorFallback');
    }, [loginMutation.error, t]);

    const resendErrorMessage = useMemo(() => {
        const error = resendMutation.error;
        if (!error) return '';
        if (typeof error === 'string') return error;
        if (error instanceof Error && error.message) return error.message;
        return t('login.resendError');
    }, [resendMutation.error, t]);

    const formErrorMessage = formErrorKey ? t(`common.errors.${formErrorKey}`) : '';
    const errorMessage = formErrorMessage || apiErrorMessage;

    useEffect(() => {
        if (token) {
            navigate('/app', { replace: true });
            return;
        }
        if (isRefreshIdle) {
            refreshSession();
        }
    }, [isRefreshIdle, navigate, refreshSession, token]);

    if (!token && isRefreshPending) {
        return <LoadingPage />;
    }

    const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        if (!email.trim()) {
            setFormErrorKey('requiredEmail');
            return;
        }
        if (!password.trim()) {
            setFormErrorKey('requiredPassword');
            return;
        }
        if (!isValidEmail(email)) {
            setFormErrorKey('invalidEmail');
            return;
        }
        if (!isValidPassword(password)) {
            setFormErrorKey('invalidPassword');
            return;
        }
        setFormErrorKey('');
        setResendComplete(false);
        loginMutation.mutate({ email, password, remember_me: rememberMe });
    };

    return (
        <Container className="flex-col justify-start pt-28">
            <div className="w-full max-w-md space-y-6">
                <AuthHeader />
                <Card className="animate-fade-up p-8" variant="strong">
                    <div className="space-y-3 text-center">
                        <h2 className="font-display text-3xl font-semibold">{t('login.title')}</h2>
                        <p className="text-sm text-muted">{t('login.subtitle')}</p>
                    </div>

                    <form className="mt-6 space-y-4" onSubmit={handleSubmit} noValidate>
                        <Input
                            id="login-email"
                            type="email"
                            label={t('common.fields.emailLabel')}
                            placeholder={t('common.fields.emailPlaceholder')}
                            value={email}
                            onChange={(event) => {
                                const next = event.target.value;
                                setEmail(next);
                                if (formErrorKey === 'requiredEmail' && next.trim()) {
                                    setFormErrorKey('');
                                } else if (formErrorKey === 'invalidEmail' && isValidEmail(next)) {
                                    setFormErrorKey('');
                                }
                            }}
                            required
                        />
                        <Input
                            id="login-password"
                            type="password"
                            label={t('common.fields.passwordLabel')}
                            placeholder={t('common.fields.passwordPlaceholder')}
                            value={password}
                            onChange={(event) => {
                                const next = event.target.value;
                                setPassword(next);
                                if (formErrorKey === 'requiredPassword' && next.trim()) {
                                    setFormErrorKey('');
                                } else if (
                                    formErrorKey === 'invalidPassword' &&
                                    isValidPassword(next)
                                ) {
                                    setFormErrorKey('');
                                }
                            }}
                            required
                        />

                        <div className="flex items-center justify-between text-xs text-muted">
                            <label className="flex items-center gap-2">
                                <input
                                    type="checkbox"
                                    className="h-4 w-4 rounded border-slate-300 text-slate-900 focus:ring-slate-400 dark:border-slate-600 dark:text-white"
                                    checked={rememberMe}
                                    onChange={(event) => setRememberMe(event.target.checked)}
                                />
                                <span>{t('login.remember')}</span>
                            </label>
                            <button
                                type="button"
                                onClick={() => navigate('/forgot')}
                                className="text-link"
                            >
                                {t('login.forgot')}
                            </button>
                        </div>

                        <ErrorMessage message={errorMessage} />

                        {emailNotVerified ? (
                            <div className="rounded-xl border border-slate-200/70 bg-white/60 px-3 py-3 text-xs text-slate-700 dark:border-slate-700/60 dark:bg-slate-900/40 dark:text-slate-200">
                                <div className="font-semibold">{t('login.verifyPrompt')}</div>
                                <p className="mt-1 text-[11px] text-slate-500 dark:text-slate-400">
                                    {t('login.verifyPromptHint')}
                                </p>
                                <div className="mt-3 flex flex-col gap-2">
                                    <Button
                                        type="button"
                                        onClick={() => resendMutation.mutate({ email })}
                                        disabled={resendMutation.isPending}
                                        fullWidth
                                    >
                                        {resendMutation.isPending
                                            ? t('login.resending')
                                            : t('login.resendButton')}
                                    </Button>
                                    {resendComplete ? (
                                        <div className="text-[11px] text-emerald-600">
                                            {t('login.resendSuccess')}
                                        </div>
                                    ) : null}
                                    {!resendComplete && resendErrorMessage ? (
                                        <div className="text-[11px] text-rose-500">
                                            {resendErrorMessage}
                                        </div>
                                    ) : null}
                                </div>
                            </div>
                        ) : null}

                        <Button type="submit" fullWidth disabled={loginMutation.isPending}>
                            {loginMutation.isPending ? t('login.signingIn') : t('login.signIn')}
                        </Button>
                    </form>

                    <div className="mt-6 flex items-center justify-between text-xs text-muted">
                        <span>
                            {t('login.noAccount')}{' '}
                            <button
                                type="button"
                                onClick={() => navigate('/signup')}
                                className="text-link"
                            >
                                {t('login.createAccount')}
                            </button>
                        </span>
                    </div>
                </Card>
            </div>
        </Container>
    );
}

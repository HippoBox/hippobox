import { useEffect, useMemo, useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useSearchParams } from 'react-router-dom';

import { Button } from '../components/Button';
import { Card } from '../components/Card';
import { Container } from '../components/Container';
import { ErrorMessage } from '../components/ErrorMessage';
import { Input } from '../components/Input';
import { AuthHeader } from '../components/AuthHeader';
import { useResetPasswordMutation } from '../hooks/useAuth';
import { useLoginEnabled } from '../hooks/useFeatures';
import { isValidPassword } from '../utils/validation';

type FormErrorKey =
    | ''
    | 'requiredPassword'
    | 'invalidPassword'
    | 'requiredConfirmPassword'
    | 'passwordMismatch';

type RuleItemProps = { label: string; isValid: boolean };

function RuleItem({ label, isValid }: RuleItemProps) {
    return (
        <div className="flex items-center gap-2 text-xs">
            <span
                className={`rule-indicator flex h-5 w-5 items-center justify-center rounded-full border ${
                    isValid
                        ? 'rule-indicator--valid border-emerald-500/50 bg-emerald-500/15 text-emerald-500'
                        : 'rule-indicator--invalid border-rose-500/40 bg-rose-500/10 text-rose-500'
                }`}
                aria-hidden="true"
            >
                {isValid ? (
                    <svg
                        viewBox="0 0 24 24"
                        className="h-3.5 w-3.5"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2.5"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                    >
                        <path d="M20 6L9 17l-5-5" />
                    </svg>
                ) : (
                    <svg
                        viewBox="0 0 24 24"
                        className="h-3.5 w-3.5"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2.5"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                    >
                        <path d="M18 6L6 18M6 6l12 12" />
                    </svg>
                )}
            </span>
            <span className={isValid ? 'text-emerald-500' : 'text-muted'}>{label}</span>
        </div>
    );
}

export function ResetPasswordPage() {
    const { t } = useTranslation();
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const token = searchParams.get('token') ?? '';
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [errorKey, setErrorKey] = useState<FormErrorKey>('');
    const [done, setDone] = useState(false);
    const { loginEnabled } = useLoginEnabled();

    const resetMutation = useResetPasswordMutation({
        onSuccess: () => {
            setDone(true);
        },
    });

    const apiErrorMessage = useMemo(() => {
        const error = resetMutation.error;
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
                const message = (detail as { message?: unknown }).message;
                if (typeof message === 'string' && message) return message;
            }
        }

        return t('resetPassword.errorFallback');
    }, [resetMutation.error, t]);

    useEffect(() => {
        if (loginEnabled) return;
        navigate('/app', { replace: true });
    }, [loginEnabled, navigate]);

    if (!loginEnabled) {
        return null;
    }

    if (!token) {
        return (
            <Container className="flex-col justify-start pt-24">
                <div className="w-full max-w-md space-y-6">
                    <AuthHeader />
                    <Card className="animate-fade-up p-8" variant="strong">
                        <div className="space-y-3 text-center">
                            <h2 className="font-display text-3xl font-semibold">
                                {t('resetPassword.invalidTitle')}
                            </h2>
                            <p className="text-sm text-muted">
                                {t('resetPassword.invalidSubtitle')}
                            </p>
                        </div>

                        <div className="mt-6 grid gap-3">
                            <Button type="button" onClick={() => navigate('/forgot')} fullWidth>
                                {t('resetPassword.requestNew')}
                            </Button>
                            <Button
                                type="button"
                                variant="outline"
                                onClick={() => navigate('/')}
                                fullWidth
                            >
                                {t('resetPassword.backToLogin')}
                            </Button>
                        </div>
                    </Card>
                </div>
            </Container>
        );
    }

    if (done) {
        return (
            <Container className="flex-col justify-start pt-24">
                <div className="w-full max-w-md space-y-6">
                    <AuthHeader />
                    <Card className="animate-fade-up p-8" variant="strong">
                        <div className="space-y-3 text-center">
                            <h2 className="font-display text-3xl font-semibold">
                                {t('resetPassword.successTitle')}
                            </h2>
                            <p className="text-sm text-muted">
                                {t('resetPassword.successSubtitle')}
                            </p>
                        </div>

                        <div className="mt-6 grid gap-3">
                            <Button type="button" onClick={() => navigate('/')} fullWidth>
                                {t('resetPassword.backToLogin')}
                            </Button>
                        </div>
                    </Card>
                </div>
            </Container>
        );
    }

    const passwordRules = [
        {
            label: t('signup.rules.password.length'),
            isValid: password.length >= 8 && password.length <= 64,
        },
        {
            label: t('signup.rules.password.upper'),
            isValid: /[A-Z]/.test(password),
        },
        {
            label: t('signup.rules.password.number'),
            isValid: /\d/.test(password),
        },
        {
            label: t('signup.rules.password.symbol'),
            isValid: /[^A-Za-z0-9]/.test(password),
        },
        {
            label: t('signup.rules.password.noSpaces'),
            isValid: password.length > 0 && !/\s/.test(password),
        },
    ];

    const confirmRules = [
        {
            label: t('signup.rules.confirm.match'),
            isValid: confirmPassword.length > 0 && confirmPassword === password,
        },
    ];

    const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        if (!password.trim()) {
            setErrorKey('requiredPassword');
            return;
        }
        if (!isValidPassword(password)) {
            setErrorKey('invalidPassword');
            return;
        }
        if (!confirmPassword.trim()) {
            setErrorKey('requiredConfirmPassword');
            return;
        }
        if (password !== confirmPassword) {
            setErrorKey('passwordMismatch');
            return;
        }
        setErrorKey('');
        resetMutation.mutate({ token, new_password: password });
    };

    const formErrorMessage = errorKey ? t(`common.errors.${errorKey}`) : '';
    const errorMessage = formErrorMessage || apiErrorMessage;

    return (
        <Container className="flex-col justify-start pt-24">
            <div className="w-full max-w-md space-y-6">
                <AuthHeader />
                <Card className="animate-fade-up p-8" variant="strong">
                    <div className="space-y-3 text-center">
                        <h2 className="font-display text-3xl font-semibold">
                            {t('resetPassword.title')}
                        </h2>
                        <p className="text-sm text-muted">{t('resetPassword.subtitle')}</p>
                    </div>

                    <form className="mt-6 space-y-4" onSubmit={handleSubmit} noValidate>
                        <Input
                            id="reset-password"
                            type="password"
                            label={t('common.fields.passwordLabel')}
                            placeholder={t('common.fields.passwordPlaceholder')}
                            value={password}
                            onChange={(event) => {
                                const next = event.target.value;
                                setPassword(next);
                                if (errorKey === 'requiredPassword' && next.trim()) {
                                    setErrorKey('');
                                } else if (
                                    errorKey === 'invalidPassword' &&
                                    isValidPassword(next)
                                ) {
                                    setErrorKey('');
                                }
                            }}
                        />
                        <div className="space-y-2 rounded-xl border border-slate-200/70 bg-white/60 p-3 dark:border-slate-700/60 dark:bg-slate-900/40">
                            {passwordRules.map((rule) => (
                                <RuleItem
                                    key={rule.label}
                                    label={rule.label}
                                    isValid={rule.isValid}
                                />
                            ))}
                        </div>
                        <Input
                            id="reset-password-confirm"
                            type="password"
                            label={t('common.fields.confirmPasswordLabel')}
                            placeholder={t('common.fields.confirmPasswordPlaceholder')}
                            value={confirmPassword}
                            onChange={(event) => {
                                const next = event.target.value;
                                setConfirmPassword(next);
                                if (errorKey === 'requiredConfirmPassword' && next.trim()) {
                                    setErrorKey('');
                                } else if (errorKey === 'passwordMismatch' && next === password) {
                                    setErrorKey('');
                                }
                            }}
                        />
                        <div className="space-y-2 rounded-xl border border-slate-200/70 bg-white/60 p-3 dark:border-slate-700/60 dark:bg-slate-900/40">
                            {confirmRules.map((rule) => (
                                <RuleItem
                                    key={rule.label}
                                    label={rule.label}
                                    isValid={rule.isValid}
                                />
                            ))}
                        </div>

                        <ErrorMessage message={errorMessage} />

                        <Button type="submit" fullWidth disabled={resetMutation.isPending}>
                            {resetMutation.isPending
                                ? t('resetPassword.submitting')
                                : t('resetPassword.submit')}
                        </Button>
                    </form>

                    <div className="mt-6 text-xs text-muted">
                        <button type="button" onClick={() => navigate('/')} className="text-link">
                            {t('resetPassword.backToLogin')}
                        </button>
                    </div>
                </Card>
            </div>
        </Container>
    );
}

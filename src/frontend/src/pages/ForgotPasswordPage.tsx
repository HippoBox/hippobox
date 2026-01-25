import { useEffect, useMemo, useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

import { Button } from '../components/Button';
import { Card } from '../components/Card';
import { Container } from '../components/Container';
import { ErrorMessage } from '../components/ErrorMessage';
import { Input } from '../components/Input';
import { AuthHeader } from '../components/AuthHeader';
import { useRequestPasswordResetMutation } from '../hooks/useAuth';
import { useEmailEnabled, useLoginEnabled } from '../hooks/useFeatures';
import { isValidEmail } from '../utils/validation';

type FormErrorKey = '' | 'requiredEmail' | 'invalidEmail' | 'userNotFound';

export function ForgotPasswordPage() {
    const { t } = useTranslation();
    const navigate = useNavigate();
    const [email, setEmail] = useState('');
    const [errorKey, setErrorKey] = useState<FormErrorKey>('');
    const [sent, setSent] = useState(false);
    const { emailEnabled } = useEmailEnabled();
    const { loginEnabled } = useLoginEnabled();

    const requestMutation = useRequestPasswordResetMutation({
        onSuccess: () => {
            setSent(true);
        },
    });

    const apiErrorMessage = useMemo(() => {
        const error = requestMutation.error;
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
                if (code === `USER_NOT_FOUND`) {
                    setErrorKey('userNotFound');
                }

                if (typeof message === 'string' && message) return message;
            }
        }

        return t('forgot.errorFallback');
    }, [requestMutation.error, t]);

    const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        if (!email.trim()) {
            setErrorKey('requiredEmail');
            return;
        }
        if (!isValidEmail(email)) {
            setErrorKey('invalidEmail');
            return;
        }
        setErrorKey('');
        requestMutation.mutate({ email });
    };

    const errorMessage = errorKey ? t(`common.errors.${errorKey}`) : '';
    const mergedErrorMessage = errorMessage || apiErrorMessage;

    useEffect(() => {
        if (!loginEnabled) {
            navigate('/app', { replace: true });
            return;
        }
        if (emailEnabled) return;
        navigate('/', { replace: true });
    }, [emailEnabled, loginEnabled, navigate]);

    if (!loginEnabled || !emailEnabled) {
        return null;
    }

    if (sent) {
        return (
            <Container className="flex-col justify-start pt-28">
                <div className="w-full max-w-md space-y-6">
                    <AuthHeader />
                    <Card className="animate-fade-up p-8" variant="strong">
                        <div className="space-y-3 text-center">
                            <h2 className="font-display text-3xl font-semibold">
                                {t('forgot.successTitle')}
                            </h2>
                            <p className="text-sm text-muted">{t('forgot.successSubtitle')}</p>
                        </div>

                        {email ? (
                            <p className="mt-4 rounded-xl border border-slate-200/70 bg-white/60 px-3 py-2 text-xs text-slate-600 dark:border-slate-700/60 dark:bg-slate-900/40 dark:text-slate-300">
                                {t('forgot.successEmail', { email })}
                            </p>
                        ) : null}

                        <div className="mt-6 grid gap-3">
                            <Button type="button" onClick={() => navigate('/')} fullWidth>
                                {t('forgot.backToLogin')}
                            </Button>
                        </div>
                    </Card>
                </div>
            </Container>
        );
    }

    return (
        <Container className="flex-col justify-start pt-28">
            <div className="w-full max-w-md space-y-6">
                <AuthHeader />
                <Card className="animate-fade-up p-8" variant="strong">
                    <div className="space-y-3 text-center">
                        <h2 className="font-display text-3xl font-semibold">{t('forgot.title')}</h2>
                        <p className="text-sm text-muted">{t('forgot.subtitle')}</p>
                    </div>

                    <form className="mt-6 space-y-4" onSubmit={handleSubmit} noValidate>
                        <Input
                            id="forgot-email"
                            type="email"
                            label={t('common.fields.emailLabel')}
                            placeholder={t('common.fields.emailPlaceholder')}
                            value={email}
                            onChange={(event) => {
                                const next = event.target.value;
                                setEmail(next);
                                if (errorKey === 'requiredEmail' && next.trim()) {
                                    setErrorKey('');
                                } else if (errorKey === 'invalidEmail' && isValidEmail(next)) {
                                    setErrorKey('');
                                }
                            }}
                        />

                        <ErrorMessage message={mergedErrorMessage} />

                        <Button type="submit" fullWidth disabled={requestMutation.isPending}>
                            {requestMutation.isPending ? t('forgot.sending') : t('forgot.submit')}
                        </Button>
                    </form>

                    <div className="mt-6 text-xs text-muted">
                        <button type="button" onClick={() => navigate('/')} className="text-link">
                            {t('forgot.backToLogin')}
                        </button>
                    </div>
                </Card>
            </div>
        </Container>
    );
}

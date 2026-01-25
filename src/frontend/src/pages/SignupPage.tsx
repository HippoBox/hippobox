import { useEffect, useMemo, useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

import { Button } from '../components/Button';
import { Card } from '../components/Card';
import { Container } from '../components/Container';
import { ErrorMessage } from '../components/ErrorMessage';
import { Input } from '../components/Input';
import { AuthHeader } from '../components/AuthHeader';
import { useSignupMutation } from '../hooks/useAuth';
import { useLoginEnabled } from '../hooks/useFeatures';
import { isValidEmail, isValidName, isValidPassword } from '../utils/validation';

type FormErrorKey =
    | ''
    | 'requiredName'
    | 'invalidName'
    | 'requiredEmail'
    | 'invalidEmail'
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

export function SignupPage() {
    const { t } = useTranslation();
    const navigate = useNavigate();
    const [name, setName] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [errorKey, setErrorKey] = useState<FormErrorKey>('');
    const { loginEnabled } = useLoginEnabled();

    const signupMutation = useSignupMutation({
        onSuccess: () => {
            if (!loginEnabled) {
                navigate('/app', { replace: true });
                return;
            }
            navigate('/signup/success', { state: { email } });
        },
    });

    useEffect(() => {
        if (loginEnabled) return;
        navigate('/app', { replace: true });
    }, [loginEnabled, navigate]);

    if (!loginEnabled) {
        return null;
    }

    const apiErrorMessage = useMemo(() => {
        const error = signupMutation.error;
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
                if (code === 'EMAIL_ALREADY_EXISTS') return t('common.errors.emailExists');
                if (code === 'NAME_ALREADY_EXISTS') return t('common.errors.nameExists');
                if (typeof message === 'string' && message) return message;
            }
        }

        return t('signup.errorFallback');
    }, [signupMutation.error, t]);

    const nameRules = [
        {
            label: t('signup.rules.name.length'),
            isValid: name.trim().length >= 2 && name.trim().length <= 30,
        },
        {
            label: t('signup.rules.name.charset'),
            isValid: name.trim().length === 0 ? false : isValidName(name),
        },
    ];

    const emailRules = [
        {
            label: t('signup.rules.email.format'),
            isValid: email.trim().length > 0 && isValidEmail(email),
        },
    ];

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
        if (!name.trim()) {
            setErrorKey('requiredName');
            return;
        }
        if (!isValidName(name)) {
            setErrorKey('invalidName');
            return;
        }
        if (!email.trim()) {
            setErrorKey('requiredEmail');
            return;
        }
        if (!isValidEmail(email)) {
            setErrorKey('invalidEmail');
            return;
        }
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
        signupMutation.mutate({ name, email, password });
    };

    const formErrorMessage = errorKey ? t(`common.errors.${errorKey}`) : '';
    const errorMessage = formErrorMessage || apiErrorMessage;

    return (
        <Container className="flex-col justify-start pt-28">
            <div className="w-full max-w-md space-y-6">
                <AuthHeader />
                <Card className="animate-fade-up p-8" variant="strong">
                    <div className="space-y-3 text-center">
                        <h2 className="font-display text-3xl font-semibold">{t('signup.title')}</h2>
                        <p className="text-sm text-muted">{t('signup.subtitle')}</p>
                    </div>

                    <form className="mt-6 space-y-4" onSubmit={handleSubmit} noValidate>
                        <Input
                            id="signup-name"
                            type="text"
                            label={t('common.fields.nameLabel')}
                            placeholder={t('common.fields.namePlaceholder')}
                            value={name}
                            onChange={(event) => {
                                const next = event.target.value;
                                setName(next);
                                if (errorKey === 'requiredName' && next.trim()) {
                                    setErrorKey('');
                                } else if (errorKey === 'invalidName' && isValidName(next)) {
                                    setErrorKey('');
                                }
                            }}
                        />
                        <div className="space-y-2 rounded-xl border border-slate-200/70 bg-white/60 p-3 dark:border-slate-700/60 dark:bg-slate-900/40">
                            {nameRules.map((rule) => (
                                <RuleItem
                                    key={rule.label}
                                    label={rule.label}
                                    isValid={rule.isValid}
                                />
                            ))}
                        </div>
                        <Input
                            id="signup-email"
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
                        <div className="space-y-2 rounded-xl border border-slate-200/70 bg-white/60 p-3 dark:border-slate-700/60 dark:bg-slate-900/40">
                            {emailRules.map((rule) => (
                                <RuleItem
                                    key={rule.label}
                                    label={rule.label}
                                    isValid={rule.isValid}
                                />
                            ))}
                        </div>
                        <Input
                            id="signup-password"
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
                            id="signup-password-confirm"
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

                        <Button type="submit" fullWidth disabled={signupMutation.isPending}>
                            {signupMutation.isPending ? t('signup.signingUp') : t('signup.submit')}
                        </Button>
                    </form>

                    <div className="mt-6 text-xs text-muted">
                        <button type="button" onClick={() => navigate('/')} className="text-link">
                            {t('signup.backToLogin')}
                        </button>
                    </div>
                </Card>
            </div>
        </Container>
    );
}

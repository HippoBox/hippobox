import { useTranslation } from 'react-i18next';
import { useLocation, useNavigate } from 'react-router-dom';

import { Button } from '../components/Button';
import { Card } from '../components/Card';
import { Container } from '../components/Container';
import { AuthHeader } from '../components/AuthHeader';

type SignupSuccessState = { email?: string };

export function SignupSuccessPage() {
    const { t } = useTranslation();
    const navigate = useNavigate();
    const location = useLocation();
    const state = (location.state as SignupSuccessState | null) ?? null;
    const email = state?.email?.trim() ?? '';

    return (
        <Container className="flex-col justify-start pt-24">
            <div className="w-full max-w-md space-y-6">
                <AuthHeader />
                <Card className="animate-fade-up p-8" variant="strong">
                    <div className="space-y-3 text-center">
                        <h2 className="font-display text-3xl font-semibold">
                            {t('signupSuccess.title')}
                        </h2>
                    </div>

                    {email ? (
                        <p className="mt-4 rounded-xl border border-slate-200/70 bg-white/60 px-3 py-2 text-xs text-slate-600 dark:border-slate-700/60 dark:bg-slate-900/40 dark:text-slate-300">
                            {t('signupSuccess.emailSentTo', { email })}
                        </p>
                    ) : (
                        <p className="mt-4 rounded-xl border border-slate-200/70 bg-white/60 px-3 py-2 text-xs text-slate-600 dark:border-slate-700/60 dark:bg-slate-900/40 dark:text-slate-300">
                            {t('signupSuccess.emailSent')}
                        </p>
                    )}

                    <div className="mt-6 grid gap-3">
                        <Button type="button" onClick={() => navigate('/')} fullWidth>
                            {t('signupSuccess.goToLogin')}
                        </Button>
                    </div>
                </Card>
            </div>
        </Container>
    );
}

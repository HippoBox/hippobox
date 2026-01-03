import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

import { Button } from '../components/Button';
import { Card } from '../components/Card';
import { Container } from '../components/Container';
import { AuthHeader } from '../components/AuthHeader';

export function VerifyEmailFailurePage() {
    const { t } = useTranslation();
    const navigate = useNavigate();

    return (
        <Container className="flex-col justify-start pt-24">
            <div className="w-full max-w-md space-y-6">
                <AuthHeader />
                <Card className="animate-fade-up p-8" variant="strong">
                    <div className="space-y-3 text-center">
                        <h2 className="font-display text-3xl font-semibold">
                            {t('verifyEmail.failureTitle')}
                        </h2>
                        <p className="text-sm text-muted">{t('verifyEmail.failureSubtitle')}</p>
                    </div>

                    <div className="mt-6 grid gap-3">
                        <Button type="button" onClick={() => navigate('/')} fullWidth>
                            {t('verifyEmail.goToLogin')}
                        </Button>
                        <Button
                            type="button"
                            variant="outline"
                            onClick={() => navigate('/signup')}
                            fullWidth
                        >
                            {t('verifyEmail.goToSignup')}
                        </Button>
                    </div>
                </Card>
            </div>
        </Container>
    );
}

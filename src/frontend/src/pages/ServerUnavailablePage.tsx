import { useTranslation } from 'react-i18next';
import { Button } from '../components/Button';
import { Card } from '../components/Card';
import { Container } from '../components/Container';

export function ServerUnavailablePage({ retry, pending }: { retry: () => void; pending: boolean }) {
    const { t } = useTranslation();
    return (
        <Container>
            <Card className="w-full max-w-lg space-y-6 p-8">
                <h1 className="text-2xl font-semibold">{t('serverUnavailable.title')}</h1>
                <p role="status">{t('serverUnavailable.message')}</p>
                <Button onClick={retry} disabled={pending}>
                    {t(pending ? 'serverUnavailable.pending' : 'serverUnavailable.retry')}
                </Button>
            </Card>
        </Container>
    );
}

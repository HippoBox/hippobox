import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';

import { Button } from '../components/Button';
import { Container } from '../components/Container';

type StandaloneNotFoundProps = {
    basePath: string;
};

export function StandaloneNotFound({ basePath }: StandaloneNotFoundProps) {
    const { t } = useTranslation();

    useEffect(() => {
        document.title = t('error.notFoundTitle');
    }, [t]);

    return (
        <Container className="flex-col justify-center pt-24">
            <div className="w-full max-w-xl space-y-6 text-center">
                <div className="flex flex-col items-center justify-center gap-3">
                    <div className="font-display text-7xl font-semibold tracking-[0.2em] text-slate-400 dark:text-slate-500">
                        404
                    </div>
                </div>
                <div className="space-y-3">
                    <h1 className="font-display text-4xl font-semibold">
                        {t('error.notFoundTitle')}
                    </h1>
                    <p className="text-sm text-muted">{t('error.notFoundSubtitle')}</p>
                </div>
                <div className="flex flex-col items-center justify-center gap-3 sm:flex-row">
                    <Button type="button" onClick={() => window.location.replace(basePath)}>
                        {t('error.actionHome')}
                    </Button>
                    <Button type="button" variant="outline" onClick={() => window.history.back()}>
                        {t('error.actionBack')}
                    </Button>
                </div>
            </div>
        </Container>
    );
}

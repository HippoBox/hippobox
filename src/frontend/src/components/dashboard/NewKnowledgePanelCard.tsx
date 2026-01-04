import { useTranslation } from 'react-i18next';
import { ArrowRight, Sparkles } from 'lucide-react';

import { Button } from '../Button';
import { Card } from '../Card';

type NewKnowledgePanelCardProps = {
    onCreate: () => void;
};

export function NewKnowledgePanelCard({ onCreate }: NewKnowledgePanelCardProps) {
    const { t } = useTranslation();

    return (
        <Card className="animate-fade-up p-6 sm:p-8" variant="strong">
            <div className="flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
                <div className="space-y-2">
                    <div className="flex items-center gap-2 text-sm font-semibold">
                        <Sparkles className="h-4 w-4 text-muted" aria-hidden="true" />
                        <span>{t('main.newKnowledgePanel.cardTitle')}</span>
                    </div>
                    <p className="max-w-xl text-sm text-muted">
                        {t('main.newKnowledgePanel.cardSubtitle')}
                    </p>
                </div>
                <Button type="button" onClick={onCreate}>
                    {t('main.newKnowledgePanel.button')}
                    <ArrowRight className="h-4 w-4" aria-hidden="true" />
                </Button>
            </div>
        </Card>
    );
}

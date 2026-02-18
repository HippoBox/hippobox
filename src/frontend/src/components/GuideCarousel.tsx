import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Rocket } from 'lucide-react';

import { Button } from './Button';

type GuideCarouselProps = {
    onClose?: () => void;
    className?: string;
};

export function GuideCarousel({ onClose, className }: GuideCarouselProps) {
    const { t } = useTranslation();
    const [activeIndex, setActiveIndex] = useState(0);

    const steps = useMemo(
        () => [
            {
                id: 'overview',
                title: t('guide.steps.overview.title'),
                description: t('guide.steps.overview.body'),
                image: '/guide/step-1.png',
            },
            {
                id: 'core_features',
                title: t('guide.steps.core.title'),
                description: t('guide.steps.core.body'),
                image: '/guide/step-2.png',
            },
            {
                id: 'hippo_search',
                title: t('guide.steps.hippoSearch.title'),
                description: t('guide.steps.hippoSearch.body'),
                image: '/guide/step-3.png',
            },
            {
                id: 'setup_mcp',
                title: t('guide.steps.setupMcp.title'),
                description: t('guide.steps.setupMcp.body'),
                image: '/guide/step-4.png',
            },
            {
                id: 'mcp_request',
                title: t('guide.steps.mcpRequest.title'),
                description: t('guide.steps.mcpRequest.body'),
                images: ['/guide/step-5_1.png', '/guide/step-5_2.png'],
            },
            {
                id: 'start_hippobox',
                title: t('guide.steps.startHippobox.title'),
                description: t('guide.steps.startHippobox.body'),
                image: '/guide/step-6.png',
            },
        ],
        [t],
    );

    const totalSteps = steps.length;
    const step = steps[activeIndex];
    const isFirst = activeIndex === 0;
    const isLast = activeIndex === totalSteps - 1;

    const handleNext = () => {
        if (isLast) {
            if (onClose) {
                onClose();
            } else {
                setActiveIndex(0);
            }
            return;
        }
        setActiveIndex((prev) => Math.min(prev + 1, totalSteps - 1));
    };

    const handlePrev = () => {
        setActiveIndex((prev) => Math.max(prev - 1, 0));
    };

    return (
        <div className={`flex h-full flex-col gap-6 ${className ?? ''}`.trim()}>
            <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="space-y-1">
                    <div className="flex items-center gap-2 text-sm font-semibold uppercase tracking-[0.28em] text-muted">
                        <Rocket className="h-4 w-4" aria-hidden="true" />
                        {t('guide.title')}
                    </div>
                    {t('guide.subtitle') ? (
                        <div className="text-sm text-muted">{t('guide.subtitle')}</div>
                    ) : null}
                </div>
                {onClose ? (
                    <Button type="button" variant="outline" className="h-9 px-4" onClick={onClose}>
                        {t('guide.close')}
                    </Button>
                ) : null}
            </div>

            <div className="flex flex-1 flex-col justify-between gap-6">
                <div className="h-[380px] shrink-0 overflow-hidden rounded-[28px] sm:h-[440px]">
                    {Array.isArray((step as { images?: string[] }).images) ? (
                        <div className="grid h-full grid-rows-2 gap-3">
                            {(step as { images: string[] }).images.map((image, index) => (
                                <img
                                    key={image}
                                    src={image}
                                    alt={`${step.title} ${index + 1}`}
                                    className="block h-full w-full rounded-[22px] object-contain"
                                    loading="lazy"
                                />
                            ))}
                        </div>
                    ) : (
                        <img
                            src={(step as { image: string }).image}
                            alt={step.title}
                            className="block h-full w-full rounded-[28px] object-contain"
                            loading="lazy"
                        />
                    )}
                </div>
                <div className="space-y-3">
                    <div className="text-xs font-semibold uppercase tracking-[0.22em] text-muted">
                        {t('guide.stepLabel', { current: activeIndex + 1, total: totalSteps })}
                    </div>
                    <h4 className="text-lg font-semibold">{step.title}</h4>
                    <p className="text-sm text-muted">{step.description}</p>
                </div>
                <div className="space-y-3">
                    <div className="flex flex-wrap items-center justify-center gap-2">
                        {steps.map((item, index) => (
                            <button
                                key={item.id}
                                type="button"
                                aria-label={item.title}
                                aria-current={index === activeIndex}
                                onClick={() => setActiveIndex(index)}
                                className={`h-2.5 w-2.5 rounded-full transition ${
                                    index === activeIndex
                                        ? 'bg-[color:var(--color-text)]'
                                        : 'bg-[color:var(--color-border-strong)]'
                                }`}
                            />
                        ))}
                    </div>
                    <div className="flex flex-wrap items-center justify-center gap-2">
                        <Button
                            type="button"
                            variant="outline"
                            className="h-10 px-4"
                            disabled={isFirst}
                            onClick={handlePrev}
                        >
                            {t('guide.prev')}
                        </Button>
                        <Button type="button" className="h-10 px-4" onClick={handleNext}>
                            {isLast
                                ? onClose
                                    ? t('guide.done')
                                    : t('guide.restart')
                                : t('guide.next')}
                        </Button>
                    </div>
                </div>
            </div>
        </div>
    );
}

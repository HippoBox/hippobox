import { useEffect, useRef } from 'react';

import { KnowledgeSearchCard } from '../components/dashboard/KnowledgeSearchCard';
import { useGuideOverlay } from '../context/GuideOverlayContext';
import { useGuideSeenMutation, useMeQuery } from '../hooks/useAuth';

export function MainPage() {
    const { data: me, isPending } = useMeQuery();
    const { isOpen, openGuide } = useGuideOverlay();
    const guideSeenMutation = useGuideSeenMutation();
    const hasTriggeredRef = useRef(false);
    const guideSeen = (me as { guide_seen?: boolean | null } | undefined)?.guide_seen ?? false;
    const hasSeenGuide = Boolean(guideSeen);

    useEffect(() => {
        if (isPending) return;
        if (hasSeenGuide) return;
        if (isOpen) return;
        if (hasTriggeredRef.current) return;
        hasTriggeredRef.current = true;
        openGuide({
            onClose: () => {
                guideSeenMutation.mutate({ seen: true });
            },
        });
    }, [guideSeenMutation, hasSeenGuide, isOpen, isPending, openGuide]);

    return (
        <div className="w-full space-y-10">
            <KnowledgeSearchCard inputId="knowledge-search-primary" />
        </div>
    );
}

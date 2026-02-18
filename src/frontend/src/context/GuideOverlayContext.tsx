import { createContext, useContext, useMemo, useRef, useState, type ReactNode } from 'react';

import { Card } from '../components/Card';
import { GuideCarousel } from '../components/GuideCarousel';

type GuideOverlayContextValue = {
    isOpen: boolean;
    openGuide: (options?: { onClose?: () => void }) => void;
    closeGuide: () => void;
};

const GuideOverlayContext = createContext<GuideOverlayContextValue | null>(null);

type GuideOverlayProviderProps = {
    children: ReactNode;
};

export function GuideOverlayProvider({ children }: GuideOverlayProviderProps) {
    const [isOpen, setIsOpen] = useState(false);
    const onCloseRef = useRef<(() => void) | null>(null);

    const value = useMemo(
        () => ({
            isOpen,
            openGuide: (options?: { onClose?: () => void }) => {
                onCloseRef.current = options?.onClose ?? null;
                setIsOpen(true);
            },
            closeGuide: () => {
                setIsOpen(false);
                const callback = onCloseRef.current;
                onCloseRef.current = null;
                if (callback) {
                    callback();
                }
            },
        }),
        [isOpen],
    );

    return (
        <GuideOverlayContext.Provider value={value}>
            {children}
            {isOpen ? (
                <div className="fixed inset-0 z-50 flex items-center justify-center px-4 py-6">
                    <div
                        className="absolute inset-0 bg-slate-900/30 backdrop-blur-sm"
                        onClick={value.closeGuide}
                        aria-hidden="true"
                    />
                    <Card className="scrollbar-theme scrollbar-pad relative z-10 w-full max-w-6xl h-[min(92vh,860px)] overflow-y-auto p-6 sm:p-8">
                        <GuideCarousel onClose={value.closeGuide} />
                    </Card>
                </div>
            ) : null}
        </GuideOverlayContext.Provider>
    );
}

export const useGuideOverlay = () => {
    const context = useContext(GuideOverlayContext);
    if (!context) {
        throw new Error('useGuideOverlay must be used within GuideOverlayProvider');
    }
    return context;
};

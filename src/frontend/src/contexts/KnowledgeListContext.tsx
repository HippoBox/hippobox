import { createContext, useContext, useEffect, useMemo, useRef, type ReactNode } from 'react';
import { useLocation } from 'react-router-dom';

import { useKnowledgeListQuery, type KnowledgeResponse } from '../hooks/useKnowledge';

type KnowledgeListContextValue = {
    knowledge: KnowledgeResponse[];
    isPending: boolean;
    isError: boolean;
};

const KnowledgeListContext = createContext<KnowledgeListContextValue | null>(null);

type KnowledgeListProviderProps = {
    children: ReactNode;
    enabled?: boolean;
};

export const KnowledgeListProvider = ({ children, enabled = true }: KnowledgeListProviderProps) => {
    const location = useLocation();
    const previousPathRef = useRef<string | null>(null);
    const { data, isPending, isError, refetch } = useKnowledgeListQuery({
        enabled,
        refetchOnMount: false,
        refetchOnWindowFocus: false,
    });

    useEffect(() => {
        if (!enabled) return;
        const previousPath = previousPathRef.current;
        const currentPath = location.pathname;
        if (previousPath !== '/app' && currentPath === '/app') {
            refetch();
        }
        previousPathRef.current = currentPath;
    }, [enabled, location.pathname, refetch]);

    const value = useMemo(
        () => ({
            knowledge: data ?? [],
            isPending,
            isError,
        }),
        [data, isPending, isError],
    );

    return <KnowledgeListContext.Provider value={value}>{children}</KnowledgeListContext.Provider>;
};

export const useKnowledgeList = () => {
    const ctx = useContext(KnowledgeListContext);
    if (!ctx) {
        throw new Error('useKnowledgeList must be used within KnowledgeListProvider');
    }
    return ctx;
};

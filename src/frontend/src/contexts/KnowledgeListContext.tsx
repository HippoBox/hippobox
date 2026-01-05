import { createContext, useContext, useMemo, type ReactNode } from 'react';

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
    const { data, isPending, isError } = useKnowledgeListQuery({
        enabled,
        refetchOnMount: false,
        refetchOnWindowFocus: false,
    });

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

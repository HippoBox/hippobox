import {
    useMutation,
    useQuery,
    type UseMutationOptions,
    type UseQueryOptions,
} from '@tanstack/react-query';

import { apiClient } from '../api/client';
import type { components } from '../api/openapi';

type KnowledgeForm = components['schemas']['KnowledgeForm'];
export type KnowledgeResponse = components['schemas']['KnowledgeResponse'];
type KnowledgeListOptions = Omit<UseQueryOptions<KnowledgeResponse[]>, 'queryKey' | 'queryFn'>;

const unwrap = async <T>(promise: Promise<{ data?: T; error?: unknown }>) => {
    const { data, error } = await promise;
    if (error) throw error;
    return data as T;
};

export const useCreateKnowledgeMutation = (
    options?: UseMutationOptions<KnowledgeResponse, unknown, KnowledgeForm>,
) =>
    useMutation({
        mutationFn: (body) => unwrap(apiClient.POST('/api/v1/knowledge/', { body })),
        ...options,
    });

export const useKnowledgeListQuery = (options?: KnowledgeListOptions) =>
    useQuery({
        queryKey: ['knowledge', 'list'],
        queryFn: () => unwrap(apiClient.GET('/api/v1/knowledge/list')),
        staleTime: 1000 * 30,
        ...options,
    });

import {
    useMutation,
    useQuery,
    useQueryClient,
    type UseMutationOptions,
    type UseQueryOptions,
} from '@tanstack/react-query';

import { apiClient } from '../api/client';
import type { components } from '../api/openapi';

type KnowledgeForm = components['schemas']['KnowledgeForm'];
type KnowledgeUpdate = components['schemas']['KnowledgeUpdate'];
export type KnowledgeResponse = components['schemas']['KnowledgeResponse'];
type KnowledgeListOptions = Omit<UseQueryOptions<KnowledgeResponse[]>, 'queryKey' | 'queryFn'>;
type KnowledgeDetailOptions = Omit<UseQueryOptions<KnowledgeResponse>, 'queryKey' | 'queryFn'>;

const unwrap = async <T>(promise: Promise<{ data?: T; error?: unknown }>) => {
    const { data, error } = await promise;
    if (error) throw error;
    return data as T;
};

export const useCreateKnowledgeMutation = (
    options?: UseMutationOptions<KnowledgeResponse, unknown, KnowledgeForm>,
) => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (body) => unwrap(apiClient.POST('/api/v1/knowledge/', { body })),
        onSuccess: (data, variables, onMutateResult, context) => {
            queryClient.setQueryData<KnowledgeResponse[]>(['knowledge', 'list'], (prev) => {
                if (!prev) return [data];
                const next = prev.filter((item) => item.id !== data.id);
                return [data, ...next];
            });
            queryClient.setQueryData<KnowledgeResponse>(['knowledge', 'detail', data.id], data);
            queryClient.invalidateQueries({ queryKey: ['knowledge', 'list'] });
            queryClient.invalidateQueries({ queryKey: ['knowledge', 'detail', data.id] });
            options?.onSuccess?.(data, variables, onMutateResult, context);
        },
        ...options,
    });
};

export const useKnowledgeListQuery = (options?: KnowledgeListOptions) =>
    useQuery({
        queryKey: ['knowledge', 'list'],
        queryFn: () => unwrap(apiClient.GET('/api/v1/knowledge/list')),
        staleTime: 1000 * 30,
        ...options,
    });

export const useKnowledgeQuery = (
    knowledgeId: number | undefined,
    options?: KnowledgeDetailOptions,
) => {
    const enabled = Boolean(knowledgeId) && (options?.enabled ?? true);
    return useQuery({
        queryKey: ['knowledge', 'detail', knowledgeId],
        queryFn: () =>
            unwrap(
                apiClient.GET('/api/v1/knowledge/{knowledge_id}', {
                    params: { path: { knowledge_id: knowledgeId as number } },
                }),
            ),
        enabled,
        staleTime: 1000 * 30,
        ...options,
    });
};

type UpdateKnowledgePayload = {
    knowledgeId: number;
    body: KnowledgeUpdate;
};

export const useUpdateKnowledgeMutation = (
    options?: UseMutationOptions<KnowledgeResponse, unknown, UpdateKnowledgePayload>,
) => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ knowledgeId, body }) =>
            unwrap(
                apiClient.PUT('/api/v1/knowledge/{knowledge_id}', {
                    params: { path: { knowledge_id: knowledgeId } },
                    body,
                }),
            ),
        onSuccess: (data, variables, onMutateResult, context) => {
            queryClient.setQueryData<KnowledgeResponse[]>(['knowledge', 'list'], (prev) => {
                if (!prev) return prev;
                return prev.map((item) => (item.id === data.id ? data : item));
            });
            queryClient.setQueryData<KnowledgeResponse>(['knowledge', 'detail', data.id], data);
            queryClient.invalidateQueries({ queryKey: ['knowledge', 'list'] });
            queryClient.invalidateQueries({ queryKey: ['knowledge', 'detail', data.id] });
            options?.onSuccess?.(data, variables, onMutateResult, context);
        },
        ...options,
    });
};

type DeleteKnowledgePayload = {
    knowledgeId: number;
};

export const useDeleteKnowledgeMutation = (
    options?: UseMutationOptions<void, unknown, DeleteKnowledgePayload>,
) => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: async ({ knowledgeId }) => {
            await unwrap(
                apiClient.DELETE('/api/v1/knowledge/{knowledge_id}', {
                    params: { path: { knowledge_id: knowledgeId } },
                }),
            );
        },
        onSuccess: (_data, variables, onMutateResult, context) => {
            queryClient.setQueryData<KnowledgeResponse[]>(['knowledge', 'list'], (prev) => {
                if (!prev) return prev;
                return prev.filter((item) => item.id !== variables.knowledgeId);
            });
            queryClient.removeQueries({ queryKey: ['knowledge', 'detail', variables.knowledgeId] });
            queryClient.invalidateQueries({ queryKey: ['knowledge', 'list'] });
            queryClient.refetchQueries({ queryKey: ['knowledge', 'list'] });
            options?.onSuccess?.(_data, variables, onMutateResult, context);
        },
        ...options,
    });
};

import {
    useMutation,
    useQuery,
    useQueryClient,
    type UseMutationOptions,
    type UseQueryOptions,
} from '@tanstack/react-query';

import { apiClient } from '../api/client';
import type { components } from '../api/openapi';

export type TopicResponse = components['schemas']['TopicResponse'];
type TopicForm = components['schemas']['TopicForm'];
type TopicListOptions = Omit<UseQueryOptions<TopicResponse[]>, 'queryKey' | 'queryFn'>;

const unwrap = async <T>(promise: Promise<{ data?: T; error?: unknown }>) => {
    const { data, error } = await promise;
    if (error) throw error;
    return data as T;
};

export const useTopicsQuery = (options?: TopicListOptions) =>
    useQuery({
        queryKey: ['topics'],
        queryFn: () => unwrap(apiClient.GET('/api/v1/topic')),
        staleTime: 1000 * 60,
        ...options,
    });

export const useCreateTopicMutation = (
    options?: UseMutationOptions<TopicResponse, unknown, TopicForm>,
) => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (body) => unwrap(apiClient.POST('/api/v1/topic', { body })),
        onSuccess: (data, variables, onMutateResult, context) => {
            queryClient.invalidateQueries({ queryKey: ['topics'] });
            options?.onSuccess?.(data, variables, onMutateResult, context);
        },
        ...options,
    });
};

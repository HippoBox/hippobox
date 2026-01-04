import { useQuery, type UseQueryOptions } from '@tanstack/react-query';

import { apiClient } from '../api/client';
import type { components } from '../api/openapi';

export type TopicResponse = components['schemas']['TopicResponse'];
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

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
type KnowledgeResponse = components['schemas']['KnowledgeResponse'];

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

type DeleteTopicContext = {
    previousTopics?: TopicResponse[];
    previousKnowledge?: KnowledgeResponse[];
};

export const useDeleteTopicMutation = (
    options?: UseMutationOptions<void, unknown, number, DeleteTopicContext>,
) => {
    const queryClient = useQueryClient();
    return useMutation<void, unknown, number, DeleteTopicContext>({
        mutationFn: async (topicId: number) => {
            await unwrap(
                apiClient.DELETE('/api/v1/topic/{topic_id}', {
                    params: { path: { topic_id: topicId } },
                }),
            );
        },
        onMutate: async (topicId): Promise<DeleteTopicContext> => {
            await queryClient.cancelQueries({ queryKey: ['topics'] });
            await queryClient.cancelQueries({ queryKey: ['knowledge', 'list'] });
            const previousTopics = queryClient.getQueryData<TopicResponse[]>(['topics']);
            const previousKnowledge = queryClient.getQueryData<KnowledgeResponse[]>([
                'knowledge',
                'list',
            ]);
            if (previousTopics) {
                queryClient.setQueryData<TopicResponse[]>(
                    ['topics'],
                    previousTopics.filter((topic) => topic.id !== topicId),
                );
            }
            if (previousKnowledge && previousTopics) {
                const defaultTopic = previousTopics.find((topic) => topic.is_default);
                const deletedTopic = previousTopics.find((topic) => topic.id === topicId);
                if (defaultTopic && deletedTopic) {
                    queryClient.setQueryData<KnowledgeResponse[]>(
                        ['knowledge', 'list'],
                        previousKnowledge.map((item) =>
                            item.topic === deletedTopic.name
                                ? { ...item, topic: defaultTopic.name }
                                : item,
                        ),
                    );
                }
            }
            return { previousTopics, previousKnowledge };
        },
        onError: (error, variables, onMutateResult, context) => {
            if (onMutateResult?.previousTopics) {
                queryClient.setQueryData<TopicResponse[]>(['topics'], onMutateResult.previousTopics);
            }
            if (onMutateResult?.previousKnowledge) {
                queryClient.setQueryData<KnowledgeResponse[]>(
                    ['knowledge', 'list'],
                    onMutateResult.previousKnowledge,
                );
            }
            options?.onError?.(error, variables, onMutateResult, context);
        },
        onSuccess: (_data, variables, onMutateResult, context) => {
            queryClient.invalidateQueries({ queryKey: ['topics'] });
            queryClient.invalidateQueries({ queryKey: ['knowledge', 'list'] });
            queryClient.refetchQueries({ queryKey: ['knowledge', 'list'] });
            options?.onSuccess?.(_data, variables, onMutateResult, context);
        },
        ...options,
    });
};

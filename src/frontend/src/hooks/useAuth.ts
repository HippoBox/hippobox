import {
    useMutation,
    useQuery,
    useQueryClient,
    type UseMutationOptions,
    type UseQueryOptions,
} from '@tanstack/react-query';

import { apiClient, authedFetch, requestRefresh } from '../api/client';
import { API_ORIGIN } from '../api';
import { clearSession, setSessionFromLogin } from '../store/session';
import { useAccessToken } from './useSession';
import { useLoginEnabled } from './useFeatures';

type LoginForm = { email: string; password: string; remember_me?: boolean };
type SignupForm = { email: string; password: string; name: string };
type PasswordResetRequestPayload = { email: string };
type PasswordResetConfirmPayload = { token: string; new_password: string };
type EmailVerificationResendPayload = { email: string };
type UserResponse = { id: number; name: string; email: string };
type UpdateProfilePayload = { name: string };
type QueryOptions = Omit<UseQueryOptions<unknown>, 'queryKey' | 'queryFn'>;

const withAuth = (token?: string) =>
    token
        ? {
              headers: {
                  Authorization: `Bearer ${token}`,
              },
          }
        : {};

const unwrap = async <T>(promise: Promise<{ data?: T; error?: unknown }>) => {
    const { data, error } = await promise;
    if (error) throw error;
    return data as T;
};

export const useLoginMutation = (options?: UseMutationOptions<unknown, unknown, LoginForm>) => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (body: LoginForm) => unwrap(apiClient.POST('/api/v1/auth/login', { body })),
        ...options,
        onSuccess: (data, variables, onMutateResult, context) => {
            setSessionFromLogin(data);
            queryClient.clear();
            const user = (data as { user?: UserResponse } | undefined)?.user;
            if (user) {
                queryClient.setQueryData(['auth', 'me'], user);
            }
            options?.onSuccess?.(data, variables, onMutateResult, context);
        },
    });
};

export const useSignupMutation = (options?: UseMutationOptions<unknown, unknown, SignupForm>) =>
    useMutation({
        mutationFn: (body) => unwrap(apiClient.POST('/api/v1/auth/signup', { body })),
        ...options,
    });

export const useLogoutMutation = (
    token?: string,
    options?: UseMutationOptions<unknown, unknown, void>,
) => {
    const queryClient = useQueryClient();
    const reactiveToken = useAccessToken();
    const resolvedToken = token ?? reactiveToken ?? undefined;

    return useMutation({
        mutationFn: () => unwrap(apiClient.POST('/api/v1/auth/logout', withAuth(resolvedToken))),
        ...options,
        onSettled: (data, error, variables, onMutateResult, context) => {
            clearSession();
            queryClient.clear();
            options?.onSettled?.(data, error, variables, onMutateResult, context);
        },
    });
};

export const useRefreshTokenMutation = (options?: UseMutationOptions<unknown, unknown, void>) =>
    useMutation({
        mutationFn: () => requestRefresh(),
        ...options,
    });

export const useRequestPasswordResetMutation = (
    options?: UseMutationOptions<unknown, unknown, PasswordResetRequestPayload>,
) =>
    useMutation({
        mutationFn: (body) =>
            unwrap(apiClient.POST('/api/v1/auth/password-reset/request', { body })),
        ...options,
    });

export const useResetPasswordMutation = (
    options?: UseMutationOptions<unknown, unknown, PasswordResetConfirmPayload>,
) =>
    useMutation({
        mutationFn: (body) =>
            unwrap(apiClient.POST('/api/v1/auth/password-reset/confirm', { body })),
        ...options,
    });

export const useVerifyEmailQuery = (token: string, options?: QueryOptions) =>
    useQuery({
        queryKey: ['auth', 'verify-email', token],
        queryFn: () =>
            unwrap(
                apiClient.GET('/api/v1/auth/verify-email/{token}', {
                    params: { path: { token } },
                }),
            ),
        enabled: !!token,
        ...options,
    });

export const useResendVerificationEmailMutation = (
    options?: UseMutationOptions<unknown, unknown, EmailVerificationResendPayload>,
) =>
    useMutation({
        mutationFn: (body) => unwrap(apiClient.POST('/api/v1/auth/verify-email/resend', { body })),
        ...options,
    });

export const useMeQuery = (options?: QueryOptions) => {
    const token = useAccessToken() ?? undefined;
    const { loginEnabled } = useLoginEnabled();
    const isEnabled = options?.enabled ?? (loginEnabled ? !!token : true);

    return useQuery({
        queryKey: ['auth', 'me'],
        queryFn: () => unwrap(apiClient.GET('/api/v1/auth/me')),
        enabled: isEnabled,
        staleTime: 1000 * 60 * 5,
        ...options,
    });
};

export const useUpdateProfileMutation = (
    options?: UseMutationOptions<UserResponse, unknown, UpdateProfilePayload>,
) => {
    const queryClient = useQueryClient();
    const token = useAccessToken() ?? undefined;

    return useMutation({
        mutationFn: async (body: UpdateProfilePayload) => {
            if (!token) {
                throw { message: 'Not authenticated.' };
            }
            const response = await authedFetch(`${API_ORIGIN}/api/v1/auth/me`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify(body),
            });

            const payload = await response.json().catch(() => null);
            if (!response.ok) {
                throw payload?.detail ?? payload ?? { message: 'Failed to update profile.' };
            }
            return payload as UserResponse;
        },
        ...options,
        onSuccess: (data, variables, onMutateResult, context) => {
            queryClient.setQueryData(['auth', 'me'], data);
            options?.onSuccess?.(data, variables, onMutateResult, context);
        },
    });
};

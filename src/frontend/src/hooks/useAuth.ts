import {
    useMutation,
    useQuery,
    type UseMutationOptions,
    type UseQueryOptions,
} from '@tanstack/react-query';

import { apiClient } from '../api/client';

type LoginForm = { email: string; password: string };
type SignupForm = { email: string; password: string; name: string };
type RefreshTokenPayload = { refresh_token: string; user_id: number };
type PasswordResetRequestPayload = { email: string };
type PasswordResetConfirmPayload = { token: string; new_password: string };
type EmailVerificationResendPayload = { email: string };

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

export const useLoginMutation = (options?: UseMutationOptions<unknown, unknown, LoginForm>) =>
    useMutation({
        mutationFn: (body) => unwrap(apiClient.POST('/api/v1/auth/login', { body })),
        ...options,
    });

export const useSignupMutation = (options?: UseMutationOptions<unknown, unknown, SignupForm>) =>
    useMutation({
        mutationFn: (body) => unwrap(apiClient.POST('/api/v1/auth/signup', { body })),
        ...options,
    });

export const useLogoutMutation = (
    token?: string,
    options?: UseMutationOptions<unknown, unknown, void>,
) =>
    useMutation({
        mutationFn: () => unwrap(apiClient.POST('/api/v1/auth/logout', withAuth(token))),
        ...options,
    });

export const useRefreshTokenMutation = (
    options?: UseMutationOptions<unknown, unknown, RefreshTokenPayload>,
) =>
    useMutation({
        mutationFn: (body) => unwrap(apiClient.POST('/api/v1/auth/refresh', { body })),
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

export const useVerifyEmailQuery = (token: string, options?: UseQueryOptions<unknown>) =>
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
        mutationFn: (body) =>
            unwrap(apiClient.POST('/api/v1/auth/verify-email/resend', { body })),
        ...options,
    });

export const useMeQuery = (token?: string, options?: UseQueryOptions<unknown>) =>
    useQuery({
        queryKey: ['auth', 'me', token],
        queryFn: () => unwrap(apiClient.GET('/api/v1/auth/me', withAuth(token))),
        enabled: !!token,
        ...options,
    });

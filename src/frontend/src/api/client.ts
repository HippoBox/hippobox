import createClient from 'openapi-fetch';

import {
    getAccessToken,
    getRefreshToken,
    getUserId,
    setSessionFromRefresh,
    clearSession,
} from '../auth/session';
import { API_ORIGIN } from './index';
import type { paths } from './openapi';

const AUTH_RETRY_HEADER = 'x-auth-retry';
const REFRESH_PATH = '/api/v1/auth/refresh';
const SKIP_REFRESH_PATHS = new Set<string>([
    '/api/v1/auth/login',
    '/api/v1/auth/signup',
    REFRESH_PATH,
    '/api/v1/auth/password-reset/request',
    '/api/v1/auth/password-reset/confirm',
    '/api/v1/auth/verify-email/{token}',
    '/api/v1/auth/verify-email/resend',
]);

let refreshPromise: Promise<string | null> | null = null;

export const apiClient = createClient<paths>({
    baseUrl: API_ORIGIN,
});

const requestRefresh = async () => {
    if (refreshPromise) return refreshPromise;

    refreshPromise = (async () => {
        const refreshToken = getRefreshToken();
        const userId = getUserId();

        if (!refreshToken || !userId) {
            return null;
        }

        const { data, error } = await apiClient.POST(REFRESH_PATH, {
            headers: { [AUTH_RETRY_HEADER]: '1' },
            body: {
                refresh_token: refreshToken,
                user_id: userId,
            },
        });

        if (error || !data) {
            clearSession();
            return null;
        }

        setSessionFromRefresh(data);
        return (data as { access_token?: string }).access_token ?? null;
    })();

    try {
        return await refreshPromise;
    } finally {
        refreshPromise = null;
    }
};

apiClient.use({
    onRequest({ request }) {
        const token = getAccessToken();
        if (!token) return;
        if (request.headers.has('Authorization')) return;

        const headers = new Headers(request.headers);
        headers.set('Authorization', `Bearer ${token}`);
        return new Request(request, { headers });
    },
    async onResponse({ request, response, schemaPath }) {
        if (response.status !== 401) return;
        if (schemaPath && SKIP_REFRESH_PATHS.has(schemaPath)) return response;
        if (request.headers.get(AUTH_RETRY_HEADER) === '1') return response;

        const nextToken = await requestRefresh();
        if (!nextToken) return response;

        const headers = new Headers(request.headers);
        headers.set('Authorization', `Bearer ${nextToken}`);
        headers.set(AUTH_RETRY_HEADER, '1');

        return fetch(new Request(request, { headers }));
    },
});

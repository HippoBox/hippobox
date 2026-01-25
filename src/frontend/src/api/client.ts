import createClient from 'openapi-fetch';

import { clearSession, getAccessToken, setSessionFromRefresh } from '../store/session';
import { getRuntimeConfig } from '../config/runtime';
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

let refreshPromise: Promise<{ access_token?: string } | null> | null = null;

const resolveLoginPath = () => {
    const trimmed = getRuntimeConfig().frontendBasePath.trim();
    if (!trimmed || trimmed === '/') {
        return '/';
    }
    const withLeading = trimmed.startsWith('/') ? trimmed : `/${trimmed}`;
    return withLeading.replace(/\/+$/, '') || '/';
};

const normalizePathname = (value: string) => {
    if (!value) return '/';
    const trimmed = value.trim();
    if (!trimmed || trimmed === '/') return '/';
    const withLeading = trimmed.startsWith('/') ? trimmed : `/${trimmed}`;
    return withLeading.replace(/\/+$/, '') || '/';
};

const handleAuthFailure = () => {
    if (!getRuntimeConfig().loginEnabled) {
        return;
    }
    clearSession();
    if (typeof window === 'undefined') return;
    const loginPath = resolveLoginPath();
    const currentPath = normalizePathname(window.location.pathname);
    if (currentPath !== normalizePathname(loginPath)) {
        window.location.replace(loginPath);
    }
};

export const apiClient = createClient<paths>({
    baseUrl: API_ORIGIN,
    fetch: (request) => {
        const withCredentials = new Request(request, { credentials: 'include' });
        return fetch(withCredentials);
    },
});

export const authedFetch = async (input: RequestInfo | URL, init: RequestInit = {}) => {
    const headers = new Headers(init.headers);
    const token = getAccessToken();
    if (token && !headers.has('Authorization')) {
        headers.set('Authorization', `Bearer ${token}`);
    }

    const request = new Request(input, {
        ...init,
        headers,
        credentials: 'include',
    });

    const response = await fetch(request);
    if (response.status !== 401) return response;
    if (request.headers.get(AUTH_RETRY_HEADER) === '1') return response;

    const data = await requestRefresh();
    const nextToken = data?.access_token;
    if (!nextToken) return response;

    const retryHeaders = new Headers(request.headers);
    retryHeaders.set('Authorization', `Bearer ${nextToken}`);
    retryHeaders.set(AUTH_RETRY_HEADER, '1');

    return fetch(new Request(request, { headers: retryHeaders }));
};

const refreshAccessToken = async () => {
    if (!getRuntimeConfig().loginEnabled) {
        return null;
    }
    const response = await fetch(`${API_ORIGIN}${REFRESH_PATH}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            [AUTH_RETRY_HEADER]: '1',
        },
        credentials: 'include',
        body: JSON.stringify({}),
    });

    if (!response.ok) {
        handleAuthFailure();
        return null;
    }

    const data = (await response.json().catch(() => null)) as { access_token?: string } | null;
    if (!data || !data.access_token) {
        handleAuthFailure();
        return null;
    }

    setSessionFromRefresh(data);
    return data;
};

export const requestRefresh = async () => {
    if (!getRuntimeConfig().loginEnabled) {
        return null;
    }
    if (refreshPromise) return refreshPromise;

    refreshPromise = refreshAccessToken();

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
        if (!getRuntimeConfig().loginEnabled) return response;
        if (response.status !== 401) return;
        if (schemaPath && SKIP_REFRESH_PATHS.has(schemaPath)) return response;
        if (request.headers.get(AUTH_RETRY_HEADER) === '1') return response;

        const data = await requestRefresh();
        const nextToken = data?.access_token;
        if (!nextToken) return response;

        const headers = new Headers(request.headers);
        headers.set('Authorization', `Bearer ${nextToken}`);
        headers.set(AUTH_RETRY_HEADER, '1');

        return fetch(new Request(request, { headers }));
    },
});

import { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';

import { API_ORIGIN } from '../api';
import { DEFAULT_EMAIL_ENABLED } from '../config/features';
import { setRuntimeConfig } from '../config/runtime';

type AppConfigResponse = {
    email_enabled: boolean;
    frontend_base_path?: string;
    api_base_path?: string;
};

const buildConfigUrl = () => {
    const base = API_ORIGIN ? API_ORIGIN.replace(/\/+$/, '') : '';
    return `${base}/config`;
};

const fetchConfig = async () => {
    const response = await fetch(buildConfigUrl(), { credentials: 'include' });
    if (!response.ok) {
        throw new Error('Failed to load app config');
    }
    return (await response.json()) as AppConfigResponse;
};

export const useAuthConfig = () => {
    const query = useQuery({
        queryKey: ['config', 'app'],
        queryFn: fetchConfig,
        staleTime: 1000 * 60 * 5,
    });
    useEffect(() => {
        if (!query.data) return;
        setRuntimeConfig({
            emailEnabled: query.data.email_enabled ?? DEFAULT_EMAIL_ENABLED,
            frontendBasePath: query.data.frontend_base_path ?? '',
            apiBasePath: query.data.api_base_path ?? '/api/v1',
        });
    }, [query.data]);
    return query;
};

export const useEmailEnabled = () => {
    const { data, isLoading, isError } = useAuthConfig();
    return {
        emailEnabled: data?.email_enabled ?? DEFAULT_EMAIL_ENABLED,
        isLoading,
        isError,
    };
};

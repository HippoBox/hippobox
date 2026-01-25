import { BASENAME } from '../config-constants';
import { DEFAULT_EMAIL_ENABLED } from './features';

type RuntimeConfig = {
    frontendBasePath: string;
    apiBasePath: string;
    emailEnabled: boolean;
};

let runtimeConfig: RuntimeConfig = {
    frontendBasePath: BASENAME,
    apiBasePath: '/api/v1',
    emailEnabled: DEFAULT_EMAIL_ENABLED,
};

export const getRuntimeConfig = () => runtimeConfig;

export const setRuntimeConfig = (partial: Partial<RuntimeConfig>) => {
    runtimeConfig = {
        ...runtimeConfig,
        ...partial,
    };
};

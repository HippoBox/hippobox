import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

import { API_ROUTES, BASENAME, PORT, PROXY_TARGET } from './src/config-constants';

type ProxyTargetMap = Record<
    string,
    { target: string; changeOrigin: boolean; secure: boolean; ws: boolean }
>;

const normalizeBasePath = (value: string): string => {
    const trimmed = value.trim();
    if (!trimmed || trimmed === '/') {
        return '/';
    }
    const withLeading = trimmed.startsWith('/') ? trimmed : `/${trimmed}`;
    const withoutTrailing = withLeading.replace(/\/+$/, '');
    return `${withoutTrailing}/`;
};

const proxyTargets = API_ROUTES.reduce<ProxyTargetMap>((proxyObj, route) => {
    proxyObj[route] = {
        target: PROXY_TARGET,
        changeOrigin: true,
        secure: false,
        ws: true,
    };
    return proxyObj;
}, {});

export default defineConfig({
    base: normalizeBasePath(BASENAME),
    plugins: [react()],
    build: {
        outDir: 'dist',
        emptyOutDir: true,
    },
    server: {
        port: PORT,
        proxy: {
            ...proxyTargets,
        },
    },
});

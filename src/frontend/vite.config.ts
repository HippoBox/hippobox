import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import react from '@vitejs/plugin-react';
import { defineConfig, type Plugin } from 'vite';

import { API_ROUTES, BASENAME, PORT, PROXY_TARGET } from './src/config-constants';

type ProxyTargetMap = Record<
    string,
    { target: string; changeOrigin: boolean; secure: boolean; ws: boolean }
>;

const frontendRoot = path.resolve(fileURLToPath(new URL('.', import.meta.url)));

const copyDistToBackend = (): Plugin => ({
    name: 'copy-frontend-dist-to-backend',
    apply: 'build',
    async writeBundle() {
        const distDir = path.resolve(frontendRoot, 'dist');
        const backendDistDir = path.resolve(
            frontendRoot,
            '..',
            'backend',
            'hippobox',
            'static',
            'dist',
        );

        await fs.rm(backendDistDir, { recursive: true, force: true });
        await fs.mkdir(backendDistDir, { recursive: true });
        await fs.cp(distDir, backendDistDir, { recursive: true });
    },
});

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
    plugins: [react(), copyDistToBackend()],
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

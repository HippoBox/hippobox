import { Suspense, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { RouterProvider } from 'react-router-dom';

import { supportedLanguages, type Language } from './i18n';
import { LoadingPage } from './pages/LoadingPage';
import { createAppRouter } from './routes';
import { useAuthConfig } from './hooks/useFeatures';
import { getRuntimeConfig } from './config/runtime';
import { StandaloneNotFound } from './pages/StandaloneNotFound';

function App() {
    const { i18n } = useTranslation();
    const [language, setLanguage] = useState<Language>(() =>
        supportedLanguages.includes(i18n.language as Language) ? (i18n.language as Language) : 'en',
    );
    const { data: appConfig, isLoading: isConfigLoading } = useAuthConfig();
    const router = useMemo(() => {
        const runtime = getRuntimeConfig();
        const basePath = appConfig?.frontend_base_path ?? runtime.frontendBasePath;
        return createAppRouter(basePath);
    }, [appConfig]);

    const normalizedBasePath = useMemo(() => {
        const raw = appConfig?.frontend_base_path ?? getRuntimeConfig().frontendBasePath;
        const trimmed = raw.trim();
        if (!trimmed || trimmed === '/') return '/';
        const withLeading = trimmed.startsWith('/') ? trimmed : `/${trimmed}`;
        return withLeading.replace(/\/+$/, '') || '/';
    }, [appConfig]);

    useEffect(() => {
        if (!appConfig) return;
        const rawBasePath = appConfig.frontend_base_path ?? '';
        const trimmed = rawBasePath.trim();
        if (!trimmed || trimmed === '/') return;
        const normalized = trimmed.startsWith('/') ? trimmed : `/${trimmed}`;
        const withoutTrailing = normalized.replace(/\/+$/, '') || '/';
        if (withoutTrailing === '/') return;
        if (window.location.pathname === '/' || window.location.pathname === '') {
            const target = `${withoutTrailing}${window.location.search}${window.location.hash}`;
            window.location.replace(target);
        }
    }, [appConfig]);
    useEffect(() => {
        document.documentElement.lang = language;
        localStorage.setItem('lang', language);
        if (i18n.language !== language) {
            void i18n.changeLanguage(language);
        }
    }, [i18n, language]);

    useEffect(() => {
        const handleLanguageChange = (lng: string) => {
            if (supportedLanguages.includes(lng as Language)) {
                setLanguage(lng as Language);
            }
        };

        i18n.on('languageChanged', handleLanguageChange);
        return () => {
            i18n.off('languageChanged', handleLanguageChange);
        };
    }, [i18n]);

    if (isConfigLoading && !appConfig) {
        return <LoadingPage />;
    }

    if (
        normalizedBasePath !== '/' &&
        window.location.pathname !== '/' &&
        window.location.pathname !== '' &&
        !window.location.pathname.startsWith(normalizedBasePath)
    ) {
        return <StandaloneNotFound basePath={normalizedBasePath} />;
    }

    return (
        <div className="min-h-screen bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
            <Suspense fallback={<LoadingPage />}>
                <RouterProvider router={router} />
            </Suspense>
        </div>
    );
}

export default App;

import { Suspense, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { RouterProvider } from 'react-router-dom';

import { supportedLanguages, type Language } from './i18n';
import { LoadingPage } from './pages/LoadingPage';
import router from './routes';

type Theme = 'light' | 'dark';

const getInitialTheme = (): Theme => {
    if (typeof window === 'undefined') {
        return 'light';
    }
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
};

function App() {
    const { i18n } = useTranslation();
    const [language, setLanguage] = useState<Language>(() =>
        supportedLanguages.includes(i18n.language as Language) ? (i18n.language as Language) : 'en',
    );
    const [theme, setTheme] = useState<Theme>(getInitialTheme);

    useEffect(() => {
        document.documentElement.classList.toggle('dark', theme === 'dark');
    }, [theme]);

    useEffect(() => {
        const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
        const handleChange = (event: MediaQueryListEvent) => {
            setTheme(event.matches ? 'dark' : 'light');
        };
        // Initialize in case the preference changed before effect ran.
        setTheme(mediaQuery.matches ? 'dark' : 'light');
        if (mediaQuery.addEventListener) {
            mediaQuery.addEventListener('change', handleChange);
            return () => mediaQuery.removeEventListener('change', handleChange);
        }
        mediaQuery.addListener(handleChange);
        return () => mediaQuery.removeListener(handleChange);
    }, []);

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

    return (
        <div className="min-h-screen bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
            <Suspense fallback={<LoadingPage />}>
                <RouterProvider router={router} />
            </Suspense>
        </div>
    );
}

export default App;

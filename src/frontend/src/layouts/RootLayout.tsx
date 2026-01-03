import { useEffect, useMemo } from 'react';
import { Outlet, useMatches } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

type RouteHandle = {
    titleKey?: string;
};

const DEFAULT_APP_NAME = 'HippoBox';
const DEFAULT_TEMPLATE = '{{page}} | {{app}}';

const normalizeTitle = (value: string | undefined | null) => (value ?? '').trim();

const resolveTitleKey = (matches: Array<{ handle?: unknown }>): string | undefined => {
    for (let i = matches.length - 1; i >= 0; i -= 1) {
        const handle = matches[i]?.handle as RouteHandle | undefined;
        if (handle?.titleKey) {
            return handle.titleKey;
        }
    }
    return undefined;
};

const formatDocumentTitle = (pageTitle: string, appName: string, template: string): string => {
    const normalizedPage = normalizeTitle(pageTitle);
    const normalizedApp = normalizeTitle(appName) || DEFAULT_APP_NAME;
    if (!normalizedPage) {
        return normalizedApp;
    }
    const lowerPage = normalizedPage.toLowerCase();
    const lowerApp = normalizedApp.toLowerCase();
    if (lowerPage === lowerApp || lowerPage.includes(lowerApp)) {
        return normalizedPage;
    }
    return template.replace('{{page}}', normalizedPage).replace('{{app}}', normalizedApp);
};

export const RootLayout = () => {
    const { t } = useTranslation();
    const matches = useMatches();

    const { appName: appNameFromDom, template: templateFromDom } = useMemo(readTitleDefaults, []);
    const titleKey = useMemo(() => resolveTitleKey(matches), [matches]);
    const appName = t('meta.appName', {
        defaultValue: appNameFromDom || DEFAULT_APP_NAME,
    });
    const template = t('meta.titleTemplate', {
        defaultValue: templateFromDom || DEFAULT_TEMPLATE,
    });

    const pageTitle = titleKey ? t(titleKey) : '';
    const resolvedPageTitle = pageTitle === titleKey ? '' : pageTitle;
    const documentTitle = useMemo(
        () => formatDocumentTitle(resolvedPageTitle, appName, template),
        [resolvedPageTitle, appName, template],
    );

    useEffect(() => {
        document.title = documentTitle;
    }, [documentTitle]);

    return <Outlet />;
};
const readTitleDefaults = () => {
    if (typeof document === 'undefined') {
        return { appName: undefined, template: undefined };
    }
    const titleElement = document.querySelector('title');
    return {
        appName: titleElement?.dataset.appName,
        template: titleElement?.dataset.titleTemplate,
    };
};

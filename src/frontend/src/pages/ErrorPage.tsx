import { useEffect, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { isRouteErrorResponse, useNavigate, useRouteError } from 'react-router-dom';

import { Button } from '../components/Button';
import { Container } from '../components/Container';
import { useAccessToken } from '../hooks/useSession';

const DEFAULT_APP_NAME = 'HippoBox';
const DEFAULT_TEMPLATE = '{{page}} | {{app}}';

const normalizeTitle = (value: string | undefined | null) => (value ?? '').trim();

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

const extractErrorInfo = (error: unknown) => {
    if (isRouteErrorResponse(error)) {
        let message: string | undefined;
        const data = error.data;
        if (typeof data === 'string' && data.trim()) {
            message = data;
        } else if (data && typeof data === 'object') {
            const payload = data as { message?: unknown };
            if (typeof payload.message === 'string' && payload.message.trim()) {
                message = payload.message;
            }
        }
        return {
            status: error.status,
            statusText: error.statusText,
            message,
        };
    }

    if (error instanceof Error) {
        return {
            status: undefined,
            statusText: undefined,
            message: error.message,
        };
    }

    return {
        status: undefined,
        statusText: undefined,
        message: undefined,
    };
};

type ErrorPageProps = {
    statusOverride?: number;
};

export function ErrorPage({ statusOverride }: ErrorPageProps) {
    const { t } = useTranslation();
    const error = useRouteError();
    const navigate = useNavigate();
    const token = useAccessToken();

    const { status, statusText, message } = useMemo(() => extractErrorInfo(error), [error]);
    const resolvedStatus = statusOverride ?? status;
    const isNotFound = resolvedStatus === 404;
    const title = t(isNotFound ? 'error.notFoundTitle' : 'error.genericTitle');
    const subtitle = t(isNotFound ? 'error.notFoundSubtitle' : 'error.genericSubtitle');
    const badgeLabel = resolvedStatus ? String(resolvedStatus) : t('error.badge');
    const detail = !isNotFound ? message || statusText : undefined;
    const homeTarget = token ? '/app' : '/';

    useEffect(() => {
        if (typeof document === 'undefined') {
            return;
        }
        const appName = t('meta.appName', { defaultValue: DEFAULT_APP_NAME });
        const template = t('meta.titleTemplate', { defaultValue: DEFAULT_TEMPLATE });
        document.title = formatDocumentTitle(title, appName, template);
    }, [t, title]);

    return (
        <Container className="flex-col justify-center pt-24">
            <div className="w-full max-w-xl space-y-6 text-center">
                <div className="flex flex-col items-center justify-center gap-3">
                    {isNotFound ? (
                        <div className="font-display text-7xl font-semibold tracking-[0.2em] text-slate-400 dark:text-slate-500">
                            404
                        </div>
                    ) : null}
                    {isNotFound ? null : <span className="badge-chip">{badgeLabel}</span>}
                </div>
                <div className="space-y-3">
                    <h1 className="font-display text-4xl font-semibold">{title}</h1>
                    <p className="text-sm text-muted">{subtitle}</p>
                    {detail ? <p className="text-xs text-muted">{detail}</p> : null}
                </div>
                <div className="flex flex-col items-center justify-center gap-3 sm:flex-row">
                    <Button type="button" onClick={() => navigate(homeTarget)}>
                        {t('error.actionHome')}
                    </Button>
                    {isNotFound ? (
                        <Button type="button" variant="outline" onClick={() => navigate(-1)}>
                            {t('error.actionBack')}
                        </Button>
                    ) : (
                        <Button type="button" variant="outline" onClick={() => navigate(0)}>
                            {t('error.actionRetry')}
                        </Button>
                    )}
                </div>
            </div>
        </Container>
    );
}

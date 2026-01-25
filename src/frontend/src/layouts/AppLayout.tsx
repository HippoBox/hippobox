import { Suspense, useEffect, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { BarChart3, BookPlus, Plug } from 'lucide-react';
import { Link, Navigate, Outlet } from 'react-router-dom';

import { useAccessToken } from '../hooks/useSession';
import { useLoginEnabled } from '../hooks/useFeatures';
import { Button } from '../components/Button';
import { Container } from '../components/Container';
import { useMeQuery, useRefreshTokenMutation } from '../hooks/useAuth';
import { AuthHeader } from '../components/AuthHeader';
import { ProfileMenu } from '../components/ProfileMenu';
import { LoadingPage } from '../pages/LoadingPage';
import { KnowledgeListProvider } from '../context/KnowledgeListContext';

const FALLBACK_PROFILE_NAME = 'HippoBox';

const resolveProfileName = (value: unknown) =>
    typeof value === 'string' && value.trim() ? value.trim() : FALLBACK_PROFILE_NAME;

const resolveProfileInitial = (name: string) => {
    const [initial] = Array.from(name.trim());
    return initial ? initial.toUpperCase() : 'H';
};

export const AppLayout = () => {
    const { t } = useTranslation();
    const token = useAccessToken();
    const { loginEnabled } = useLoginEnabled();
    const {
        mutate: refreshSession,
        isIdle: isRefreshIdle,
        isPending: isRefreshPending,
        isError: isRefreshError,
    } = useRefreshTokenMutation();
    const {
        data: me,
        isPending: isMePending,
        isError: isMeError,
    } = useMeQuery({
        enabled: loginEnabled ? !!token : true,
    });
    const profileName = resolveProfileName((me as { name?: unknown } | undefined)?.name);
    const profileInitial = useMemo(() => resolveProfileInitial(profileName), [profileName]);
    const avatarUrl = (me as { avatar_url?: unknown } | undefined)?.avatar_url;
    const resolvedAvatarUrl =
        typeof avatarUrl === 'string' && avatarUrl.trim() ? avatarUrl : undefined;

    useEffect(() => {
        if (!loginEnabled) {
            return;
        }
        if (!token && isRefreshIdle) {
            refreshSession();
        }
    }, [isRefreshIdle, loginEnabled, refreshSession, token]);

    if (loginEnabled && !token && isRefreshError) {
        return <Navigate to="/" replace />;
    }

    if (loginEnabled && token && isMeError) {
        return <Navigate to="/" replace />;
    }

    const isLoading = loginEnabled
        ? (!token && isRefreshPending) || (token && isMePending)
        : isMePending;

    return (
        <Container
            outerClassName="overflow-visible"
            className="flex-col items-stretch justify-start gap-10 pt-1 pb-8 min-h-0"
        >
            <nav className="sticky top-6 z-20 h-14 flex w-full items-center justify-between rounded-[28px] border border-[color:var(--color-border)] px-6 py-4 shadow-[0_12px_32px_rgba(15,23,42,0.08)]">
                <div className="pointer-events-none absolute inset-0 rounded-[28px] bg-[color:var(--color-bg)]/70 backdrop-blur-xl" />
                <Link to="/app" className="shrink-0 relative z-10" aria-label="Go to main">
                    <AuthHeader size="xs" layout="inline" />
                </Link>
                <div className="flex items-center gap-4 relative z-10">
                    <Link to="/app/new" className="shrink-0">
                        <Button type="button" className="h-9 px-4 text-xs">
                            <span className="flex items-center gap-2">
                                <BookPlus className="h-4 w-4" aria-hidden="true" />
                                {t('nav.createKnowledge')}
                            </span>
                        </Button>
                    </Link>
                    <Link to="/app/insights" className="shrink-0">
                        <Button type="button" variant="outline" className="h-9 px-4 text-xs">
                            <span className="flex items-center gap-2">
                                <BarChart3 className="h-4 w-4" aria-hidden="true" />
                                {t('nav.knowledgeInsights')}
                            </span>
                        </Button>
                    </Link>
                    <Link to="/app/mcp" className="shrink-0">
                        <Button type="button" variant="outline" className="h-9 px-4 text-xs">
                            <span className="flex items-center gap-2">
                                <Plug className="h-4 w-4" aria-hidden="true" />
                                {t('nav.mcpGuide')}
                            </span>
                        </Button>
                    </Link>
                    <ProfileMenu
                        profileName={profileName}
                        profileInitial={profileInitial}
                        avatarUrl={resolvedAvatarUrl}
                    />
                </div>
            </nav>
            <KnowledgeListProvider enabled={loginEnabled ? !!token && !isRefreshPending : true}>
                <div className="flex-1">
                    {isLoading ? (
                        <LoadingPage variant="content" />
                    ) : (
                        <Suspense fallback={<LoadingPage variant="content" />}>
                            <Outlet />
                        </Suspense>
                    )}
                </div>
            </KnowledgeListProvider>
        </Container>
    );
};

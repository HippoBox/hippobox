import { lazy } from 'react';
import { createBrowserRouter, createRoutesFromElements, Route } from 'react-router-dom';

import { BASENAME } from './config-constants';
import { AppLayout } from './layouts/AppLayout';
import { RootLayout } from './layouts/RootLayout';

const LoginPage = lazy(() =>
    import('./pages/LoginPage').then((mod) => ({ default: mod.LoginPage })),
);
const SignupPage = lazy(() =>
    import('./pages/SignupPage').then((mod) => ({ default: mod.SignupPage })),
);
const ForgotPasswordPage = lazy(() =>
    import('./pages/ForgotPasswordPage').then((mod) => ({ default: mod.ForgotPasswordPage })),
);
const MainPage = lazy(() => import('./pages/MainPage').then((mod) => ({ default: mod.MainPage })));
const NewKnowledgePage = lazy(() =>
    import('./pages/NewKnowledgePage').then((mod) => ({ default: mod.NewKnowledgePage })),
);
const KnowledgeInsightsPage = lazy(() =>
    import('./pages/KnowledgeInsightsPage').then((mod) => ({ default: mod.KnowledgeInsightsPage })),
);
const SignupSuccessPage = lazy(() =>
    import('./pages/SignupSuccessPage').then((mod) => ({ default: mod.SignupSuccessPage })),
);
const VerifyEmailSuccessPage = lazy(() =>
    import('./pages/VerifyEmailSuccessPage').then((mod) => ({
        default: mod.VerifyEmailSuccessPage,
    })),
);
const VerifyEmailFailurePage = lazy(() =>
    import('./pages/VerifyEmailFailurePage').then((mod) => ({
        default: mod.VerifyEmailFailurePage,
    })),
);
const ResetPasswordPage = lazy(() =>
    import('./pages/ResetPasswordPage').then((mod) => ({ default: mod.ResetPasswordPage })),
);
const SettingsPage = lazy(() =>
    import('./pages/SettingsPage').then((mod) => ({ default: mod.SettingsPage })),
);

const normalizeRouterBasename = (value: string): string => {
    const trimmed = value.trim();
    if (!trimmed || trimmed === '/') {
        return '/';
    }
    const withLeading = trimmed.startsWith('/') ? trimmed : `/${trimmed}`;
    return withLeading.replace(/\/+$/, '') || '/';
};

const router = createBrowserRouter(
    createRoutesFromElements(
        <>
            <Route element={<RootLayout />}>
                <Route index element={<LoginPage />} handle={{ titleKey: 'login.title' }} />
                <Route element={<AppLayout />}>
                    <Route path="app" element={<MainPage />} handle={{ titleKey: 'main.title' }} />
                    <Route
                        path="app/new"
                        element={<NewKnowledgePage />}
                        handle={{ titleKey: 'knowledgeCreate.title' }}
                    />
                    <Route
                        path="app/insights"
                        element={<KnowledgeInsightsPage />}
                        handle={{ titleKey: 'knowledgeInsights.title' }}
                    />
                    <Route
                        path="app/settings"
                        element={<SettingsPage />}
                        handle={{ titleKey: 'settings.title' }}
                    />
                </Route>
                <Route
                    path="signup"
                    element={<SignupPage />}
                    handle={{ titleKey: 'signup.title' }}
                />
                <Route
                    path="signup/success"
                    element={<SignupSuccessPage />}
                    handle={{ titleKey: 'signupSuccess.title' }}
                />
                <Route
                    path="forgot"
                    element={<ForgotPasswordPage />}
                    handle={{ titleKey: 'forgot.title' }}
                />
                <Route
                    path="verify-email/success"
                    element={<VerifyEmailSuccessPage />}
                    handle={{ titleKey: 'verifyEmail.successTitle' }}
                />
                <Route
                    path="verify-email/failure"
                    element={<VerifyEmailFailurePage />}
                    handle={{ titleKey: 'verifyEmail.failureTitle' }}
                />
                <Route
                    path="reset-password"
                    element={<ResetPasswordPage />}
                    handle={{ titleKey: 'resetPassword.title' }}
                />
            </Route>
        </>,
    ),
    { basename: normalizeRouterBasename(BASENAME) },
);

export default router;

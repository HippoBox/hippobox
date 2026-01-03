import { lazy } from 'react';
import { createBrowserRouter, createRoutesFromElements, Route } from 'react-router-dom';

import { BASENAME } from './config-constants';

const LoginPage = lazy(() =>
    import('./pages/LoginPage').then((mod) => ({ default: mod.LoginPage })),
);
const SignupPage = lazy(() =>
    import('./pages/SignupPage').then((mod) => ({ default: mod.SignupPage })),
);
const ForgotPasswordPage = lazy(() =>
    import('./pages/ForgotPasswordPage').then((mod) => ({ default: mod.ForgotPasswordPage })),
);
const MainPage = lazy(() =>
    import('./pages/MainPage').then((mod) => ({ default: mod.MainPage })),
);
const SignupSuccessPage = lazy(() =>
    import('./pages/SignupSuccessPage').then((mod) => ({ default: mod.SignupSuccessPage })),
);
const VerifyEmailSuccessPage = lazy(() =>
    import('./pages/VerifyEmailSuccessPage').then((mod) => ({ default: mod.VerifyEmailSuccessPage })),
);
const VerifyEmailFailurePage = lazy(() =>
    import('./pages/VerifyEmailFailurePage').then((mod) => ({ default: mod.VerifyEmailFailurePage })),
);
const ResetPasswordPage = lazy(() =>
    import('./pages/ResetPasswordPage').then((mod) => ({ default: mod.ResetPasswordPage })),
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
            <Route path="/" element={<LoginPage />} />
            <Route path="/app" element={<MainPage />} />
            <Route path="/signup" element={<SignupPage />} />
            <Route path="/signup/success" element={<SignupSuccessPage />} />
            <Route path="/forgot" element={<ForgotPasswordPage />} />
            <Route path="/verify-email/success" element={<VerifyEmailSuccessPage />} />
            <Route path="/verify-email/failure" element={<VerifyEmailFailurePage />} />
            <Route path="/reset-password" element={<ResetPasswordPage />} />
        </>,
    ),
    { basename: normalizeRouterBasename(BASENAME) },
);

export default router;

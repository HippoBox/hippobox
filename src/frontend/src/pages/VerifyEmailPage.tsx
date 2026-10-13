import { Navigate, useSearchParams } from 'react-router-dom';
import { useVerifyEmailQuery } from '../hooks/useAuth';
import { LoadingPage } from './LoadingPage';

export function VerifyEmailPage() {
    const [params] = useSearchParams();
    const token = params.get('token') ?? '';
    const verification = useVerifyEmailQuery(token, { retry: false });
    if (!token || verification.isError) return <Navigate to="/verify-email/failure" replace />;
    if (verification.isSuccess) return <Navigate to="/verify-email/success" replace />;
    return <LoadingPage />;
}

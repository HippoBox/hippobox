import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { API_ORIGIN } from '../api';
import { authedFetch } from '../api/client';
import { AuthHeader } from '../components/AuthHeader';
import { Button } from '../components/Button';
import { Card } from '../components/Card';
import { useAccessToken } from '../hooks/useSession';

type Consent = { client_name: string; scopes: string[]; redirect_uri: string };

export function McpConsentPage() {
    const { i18n } = useTranslation();
    const ko = i18n.language.startsWith('ko');
    const navigate = useNavigate();
    const [params] = useSearchParams();
    const requestId = params.get('request') ?? '';
    const token = useAccessToken();
    const [consent, setConsent] = useState<Consent | null>(null);
    const [identity, setIdentity] = useState('');
    const [error, setError] = useState(false);
    const [pending, setPending] = useState(false);

    useEffect(() => {
        const controller = new AbortController();
        void fetch(`${API_ORIGIN}/oauth/consent?request_id=${encodeURIComponent(requestId)}`, {
            credentials: 'include',
            signal: controller.signal,
        })
            .then(async (res) => {
                if (!res.ok) throw new Error('Invalid request');
                setConsent(await res.json());
            })
            .catch(() => {
                if (!controller.signal.aborted) setError(true);
            });
        return () => controller.abort();
    }, [requestId]);

    useEffect(() => {
        if (!token) return;
        const controller = new AbortController();
        void authedFetch(`${API_ORIGIN}/api/v1/auth/me`, { signal: controller.signal })
            .then(async (res) => {
                if (!res.ok) throw new Error('Sign in again');
                const user = await res.json();
                setIdentity(user.email);
            })
            .catch(() => {
                if (!controller.signal.aborted) setError(true);
            });
        return () => controller.abort();
    }, [token]);

    const decide = async (approve: boolean) => {
        setPending(true);
        try {
            const result = await authedFetch(`${API_ORIGIN}/oauth/consent`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ request_id: requestId, approve }),
            });
            if (!result.ok) throw new Error('Consent failed');
            const data = await result.json();
            window.location.assign(data.redirect_uri);
        } catch {
            setError(true);
            setPending(false);
        }
    };

    return (
        <main className="flex min-h-screen items-center justify-center px-4 py-12">
            <Card className="w-full max-w-lg space-y-6 p-6 sm:p-8">
                <AuthHeader />
                <h1 className="font-display text-2xl font-semibold">
                    {ko ? 'HippoBox 연결' : 'Connect HippoBox'}
                </h1>
                {error ? (
                    <p role="alert" className="text-sm text-red-500">
                        {ko
                            ? '연결 요청이 만료되었거나 처리할 수 없습니다. MCP 클라이언트에서 다시 연결해 주세요.'
                            : 'This connection request expired or could not be completed. Start again from your MCP client.'}
                    </p>
                ) : consent ? (
                    <>
                        <p className="text-sm text-muted">
                            {ko
                                ? `${consent.client_name}에서 아래 권한을 요청합니다.`
                                : `${consent.client_name} is requesting the following permissions.`}
                        </p>
                        <ul className="list-disc space-y-2 pl-5 text-sm">
                            {consent.scopes.includes('knowledge:read') && (
                                <li>
                                    {ko ? '내 지식 조회 및 검색' : 'Read and search my knowledge'}
                                </li>
                            )}
                            {consent.scopes.includes('knowledge:write') && (
                                <li>
                                    {ko
                                        ? '내 지식 생성, 수정 및 삭제'
                                        : 'Create, edit and delete my knowledge'}
                                </li>
                            )}
                        </ul>
                        <p className="break-all text-xs text-muted">
                            {ko ? '돌아갈 주소: ' : 'Return to: '}
                            {consent.redirect_uri}
                        </p>
                        {token ? (
                            <>
                                <p className="text-sm">{identity}</p>
                                <div className="flex gap-3">
                                    <Button
                                        disabled={pending || !identity}
                                        onClick={() => void decide(true)}
                                    >
                                        {ko ? '연결 허용' : 'Allow connection'}
                                    </Button>
                                    <Button
                                        variant="outline"
                                        disabled={pending || !identity}
                                        onClick={() => void decide(false)}
                                    >
                                        {ko ? '거절' : 'Deny'}
                                    </Button>
                                </div>
                            </>
                        ) : (
                            <Button
                                onClick={() =>
                                    navigate(`/?mcp_request=${encodeURIComponent(requestId)}`)
                                }
                            >
                                {ko ? '로그인하고 계속' : 'Sign in to continue'}
                            </Button>
                        )}
                    </>
                ) : (
                    <p className="text-sm text-muted">
                        {ko ? '연결 요청 확인 중…' : 'Loading connection request…'}
                    </p>
                )}
            </Card>
        </main>
    );
}

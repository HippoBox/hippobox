import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { API_ORIGIN } from '../api';
import { authedFetch } from '../api/client';
import { useAuthConfig } from '../hooks/useFeatures';
import { Button } from './Button';
import { Card } from './Card';

type Connection = { id: string; client_name: string; scopes: string[] };

export function McpOAuthPanel() {
    const { i18n } = useTranslation();
    const ko = i18n.language.startsWith('ko');
    const { data: config } = useAuthConfig();
    const enabled = config?.mcp_oauth_enabled ?? false;
    const [connections, setConnections] = useState<Connection[]>([]);
    const [failed, setFailed] = useState(false);
    const [busy, setBusy] = useState<string | null>(null);
    const mcpUrl = `${API_ORIGIN || window.location.origin}/mcp`;

    useEffect(() => {
        if (!enabled) return;
        const controller = new AbortController();
        void authedFetch(`${API_ORIGIN}/oauth/connections`, { signal: controller.signal })
            .then(async (result) => {
                if (!result.ok) throw new Error('Cannot load connections');
                setConnections(await result.json());
            })
            .catch(() => {
                if (!controller.signal.aborted) setFailed(true);
            });
        return () => controller.abort();
    }, [enabled]);

    const disconnect = async (id: string) => {
        setBusy(id);
        setFailed(false);
        try {
            const result = await authedFetch(`${API_ORIGIN}/oauth/connections/${id}`, {
                method: 'DELETE',
            });
            if (!result.ok) throw new Error('Cannot disconnect');
            setConnections((items) => items.filter((item) => item.id !== id));
        } catch {
            setFailed(true);
        } finally {
            setBusy(null);
        }
    };

    return (
        <Card className="space-y-4 p-6">
            <h3 className="font-display text-base font-semibold">ChatGPT · OAuth</h3>
            {enabled ? (
                <>
                    <ol className="list-decimal space-y-2 pl-5 text-sm text-muted">
                        <li>
                            {ko
                                ? 'ChatGPT에서 사용자 지정 MCP 서버를 추가합니다.'
                                : 'Add a custom MCP server in ChatGPT.'}
                        </li>
                        <li>
                            {ko ? '서버 URL: ' : 'Server URL: '}
                            <code className="break-all">{mcpUrl}</code>
                        </li>
                        <li>
                            {ko
                                ? '인증은 OAuth, 클라이언트 등록은 동적 클라이언트 등록(DCR)을 선택합니다.'
                                : 'Choose OAuth and Dynamic Client Registration (DCR).'}
                        </li>
                        <li>
                            {ko
                                ? '클라이언트 ID·시크릿은 입력하지 않습니다. HippoBox에 로그인하고 접근 권한을 승인하세요.'
                                : 'Leave the client ID and secret empty. Sign in to HippoBox and approve access.'}
                        </li>
                    </ol>
                    <p className="text-xs text-muted">
                        {ko ? '기본 권한 범위' : 'Default scopes'}:{' '}
                        <code>knowledge:read knowledge:write</code>
                    </p>
                </>
            ) : (
                <p className="text-sm text-muted">
                    {ko
                        ? '이 서버는 MCP OAuth가 비활성화되어 있습니다. 서버 설정에서 활성화한 뒤 ChatGPT에 연결할 수 있습니다.'
                        : 'MCP OAuth is disabled on this server. Enable it in the server configuration before connecting ChatGPT.'}
                </p>
            )}
            <a
                className="inline-block text-sm underline"
                href={`${import.meta.env.BASE_URL}hippobox-mcp-icon.png`}
                download="hippobox-mcp-icon.png"
            >
                {ko
                    ? 'ChatGPT용 아이콘 다운로드 (256×256 PNG, 4.6KB)'
                    : 'Download connector icon (256×256 PNG, 4.6KB)'}
            </a>
            {connections.length > 0 && (
                <div className="space-y-3 border-t border-slate-200 pt-4 dark:border-slate-800">
                    <h4 className="text-sm font-semibold">
                        {ko ? '연결된 MCP 클라이언트' : 'Connected MCP clients'}
                    </h4>
                    {connections.map((item) => (
                        <div
                            key={item.id}
                            className="flex flex-wrap items-center justify-between gap-3"
                        >
                            <div>
                                <p className="text-sm">{item.client_name}</p>
                                <p className="text-xs text-muted">{item.scopes.join(', ')}</p>
                            </div>
                            <Button
                                variant="outline"
                                disabled={busy !== null}
                                onClick={() => void disconnect(item.id)}
                            >
                                {ko ? '연결 해제' : 'Disconnect'}
                            </Button>
                        </div>
                    ))}
                </div>
            )}
            {failed && (
                <p role="alert" className="text-sm text-red-500">
                    {ko
                        ? '연결 정보를 처리하지 못했습니다. 페이지를 새로고침하고 다시 시도해 주세요.'
                        : 'Could not update connections. Reload this page and try again.'}
                </p>
            )}
        </Card>
    );
}

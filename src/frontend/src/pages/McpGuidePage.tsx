import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Check, Copy, KeyRound, Plug } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

import { Button } from '../components/Button';
import { Card } from '../components/Card';
import claudeLogo from '../assets/claude.svg';
import cursorLogo from '../assets/cursor.svg';
import openaiLogo from '../assets/openai-codex.svg';

const CLAUDE_CONFIG = `{
    "mcpServers": {
        "hippobox": {
            "command": "uvx",
            "args": [
                "mcp-proxy",
                "--transport",
                "streamablehttp",
                "https://hippobox.org/mcp"
            ],
            "env": {
                "API_ACCESS_TOKEN": "<YOUR_SECRET_KEY>"
            }
        }
    }
}`;

const CURSOR_CONFIG = `{
    "mcpServers": {
        "hippobox": {
            "url": "https://hippobox.org/mcp",
            "headers": {
                "Authorization": "Bearer <YOUR_SECRET_KEY>"
            }
        }
    }
}`;

const CODEX_CONFIG = `[mcp_servers.hippobox]
command = "uvx"
args = [
    "mcp-proxy",
    "--transport",
    "streamablehttp",
    "https://hippobox.org/mcp"
]
[mcp_servers.hippobox.env]
API_ACCESS_TOKEN = "<YOUR_SECRET_KEY>"`;

export function McpGuidePage() {
    const { t } = useTranslation();
    const navigate = useNavigate();
    const [copiedBlock, setCopiedBlock] = useState<string | null>(null);

    const handleCopy = async (key: string, value: string) => {
        if (!value) return;
        try {
            await navigator.clipboard.writeText(value);
            setCopiedBlock(key);
            window.setTimeout(() => setCopiedBlock(null), 1600);
        } catch {
            setCopiedBlock(null);
        }
    };
    return (
        <div className="w-full space-y-8">
            <div className="space-y-1">
                <div className="flex items-center gap-3">
                    <Plug className="h-5 w-5 text-muted" aria-hidden="true" />
                    <h2 className="font-display text-2xl font-semibold">{t('mcpGuide.title')}</h2>
                </div>
                <p className="max-w-2xl text-sm text-muted sm:text-base">
                    {t('mcpGuide.subtitle')}
                </p>
            </div>

            <div className="grid gap-6">
                <Button
                    type="button"
                    variant="outline"
                    className="h-8 px-3 text-xs w-fit"
                    onClick={() => navigate('/app/settings#apiKey')}
                >
                    <span className="flex items-center gap-2">
                        <KeyRound className="h-4 w-4" aria-hidden="true" />
                        {t('mcpGuide.cta')}
                    </span>
                </Button>
                <Card className="space-y-4 p-6">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                        <div className="inline-flex items-center gap-2 rounded-2xl border border-slate-200 bg-white/95 px-3 py-2 text-slate-900 shadow-[0_6px_16px_rgba(15,23,42,0.08)]">
                            <img src={claudeLogo} alt="" aria-hidden="true" className="h-5 w-5" />
                            <h3 className="font-display text-base font-semibold">
                                {t('mcpGuide.claude.title')}
                            </h3>
                        </div>
                        <Button
                            type="button"
                            variant="outline"
                            className="h-8 px-3 text-xs"
                            onClick={() => handleCopy('claude', CLAUDE_CONFIG)}
                            aria-live="polite"
                        >
                            <span className="flex items-center gap-2">
                                {copiedBlock === 'claude' ? (
                                    <Check className="h-3.5 w-3.5" aria-hidden="true" />
                                ) : (
                                    <Copy className="h-3.5 w-3.5" aria-hidden="true" />
                                )}
                                {copiedBlock === 'claude'
                                    ? t('mcpGuide.copied')
                                    : t('mcpGuide.copy')}
                            </span>
                        </Button>
                    </div>
                    <p className="text-sm text-muted">{t('mcpGuide.claude.description')}</p>
                    <pre className="overflow-auto rounded-2xl border border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-4 py-3 text-xs leading-relaxed text-[color:var(--color-text)]">
                        <code>{CLAUDE_CONFIG}</code>
                    </pre>
                </Card>

                <Card className="space-y-4 p-6">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                        <div className="inline-flex items-center gap-2 rounded-2xl border border-slate-200 bg-white/95 px-3 py-2 text-slate-900 shadow-[0_6px_16px_rgba(15,23,42,0.08)]">
                            <img src={cursorLogo} alt="" aria-hidden="true" className="h-5 w-5" />
                            <h3 className="font-display text-base font-semibold">
                                {t('mcpGuide.cursor.title')}
                            </h3>
                        </div>
                        <Button
                            type="button"
                            variant="outline"
                            className="h-8 px-3 text-xs"
                            onClick={() => handleCopy('cursor', CURSOR_CONFIG)}
                            aria-live="polite"
                        >
                            <span className="flex items-center gap-2">
                                {copiedBlock === 'cursor' ? (
                                    <Check className="h-3.5 w-3.5" aria-hidden="true" />
                                ) : (
                                    <Copy className="h-3.5 w-3.5" aria-hidden="true" />
                                )}
                                {copiedBlock === 'cursor'
                                    ? t('mcpGuide.copied')
                                    : t('mcpGuide.copy')}
                            </span>
                        </Button>
                    </div>
                    <p className="text-sm text-muted">{t('mcpGuide.cursor.description')}</p>
                    <pre className="overflow-auto rounded-2xl border border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-4 py-3 text-xs leading-relaxed text-[color:var(--color-text)]">
                        <code>{CURSOR_CONFIG}</code>
                    </pre>
                </Card>

                <Card className="space-y-4 p-6">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                        <div className="inline-flex items-center gap-2 rounded-2xl border border-slate-200 bg-white/95 px-3 py-2 text-slate-900 shadow-[0_6px_16px_rgba(15,23,42,0.08)]">
                            <img src={openaiLogo} alt="" aria-hidden="true" className="h-6 w-6" />
                            <h3 className="font-display text-base font-semibold">
                                {t('mcpGuide.codex.title')}
                            </h3>
                        </div>
                        <Button
                            type="button"
                            variant="outline"
                            className="h-8 px-3 text-xs"
                            onClick={() => handleCopy('codex', CODEX_CONFIG)}
                            aria-live="polite"
                        >
                            <span className="flex items-center gap-2">
                                {copiedBlock === 'codex' ? (
                                    <Check className="h-3.5 w-3.5" aria-hidden="true" />
                                ) : (
                                    <Copy className="h-3.5 w-3.5" aria-hidden="true" />
                                )}
                                {copiedBlock === 'codex'
                                    ? t('mcpGuide.copied')
                                    : t('mcpGuide.copy')}
                            </span>
                        </Button>
                    </div>
                    <p className="text-sm text-muted">{t('mcpGuide.codex.description')}</p>
                    <pre className="overflow-auto rounded-2xl border border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-4 py-3 text-xs leading-relaxed text-[color:var(--color-text)]">
                        <code>{CODEX_CONFIG}</code>
                    </pre>
                </Card>
            </div>
        </div>
    );
}

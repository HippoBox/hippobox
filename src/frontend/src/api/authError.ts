import type { TFunction } from 'i18next';

const AUTH_ERROR_KEYS = {
    EMAIL_ALREADY_EXISTS: 'common.errors.emailExists',
    NAME_ALREADY_EXISTS: 'common.errors.nameExists',
    USER_NOT_FOUND: 'common.errors.userNotFound',
    EMAIL_NOT_VERIFIED: 'login.verifyRequired',
    INVALID_CREDENTIALS: 'login.invalidCredentials',
    ACCOUNT_LOCKED: 'login.accountLocked',
} as const;

type AuthErrorCode = keyof typeof AUTH_ERROR_KEYS;
type AuthErrorDetail = {
    error?: AuthErrorCode;
    limit_count?: number;
    remaining_seconds?: number;
};

// Keep HippoBox's existing detail envelope; do not render arbitrary server messages.
export function extractAuthError(error: unknown): AuthErrorDetail | null {
    if (!error || typeof error !== 'object') return null;
    const detail = (error as { detail?: unknown }).detail;
    if (!detail || typeof detail !== 'object') return null;
    const value = detail as Record<string, unknown>;
    const code = value.error;
    const number = (input: unknown) =>
        typeof input === 'number' && Number.isFinite(input) && input >= 0 ? input : undefined;
    return {
        error:
            typeof code === 'string' && Object.hasOwn(AUTH_ERROR_KEYS, code)
                ? (code as AuthErrorCode)
                : undefined,
        limit_count: number(value.limit_count),
        remaining_seconds: number(value.remaining_seconds),
    };
}

export function resolveAuthErrorMessage(t: TFunction, error: unknown, fallbackKey: string): string {
    if (!error) return '';
    const detail = extractAuthError(error);
    if (!detail?.error) return t(fallbackKey);
    if (detail.error === 'INVALID_CREDENTIALS' && detail.limit_count === undefined)
        return t(fallbackKey);
    if (detail.error === 'ACCOUNT_LOCKED' && detail.remaining_seconds === undefined)
        return t(fallbackKey);
    return t(AUTH_ERROR_KEYS[detail.error], {
        limit_count: detail.limit_count,
        remaining_seconds: detail.remaining_seconds,
    });
}

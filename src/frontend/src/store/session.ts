type SessionState = {
    accessToken?: string;
};

const ACCESS_TOKEN_KEY = 'hippobox_access_token';
type TokenListener = () => void;
const tokenListeners = new Set<TokenListener>();

const readStoredToken = () => {
    try {
        return sessionStorage.getItem(ACCESS_TOKEN_KEY);
    } catch {
        return null;
    }
};

let memorySession: SessionState = {
    accessToken: readStoredToken() ?? undefined,
};

export const getAccessToken = () => memorySession.accessToken ?? null;

const notifyTokenListeners = () => {
    tokenListeners.forEach((listener) => listener());
};

export const subscribeToAccessToken = (listener: TokenListener) => {
    tokenListeners.add(listener);
    return () => {
        tokenListeners.delete(listener);
    };
};

export const setAccessToken = (accessToken: string) => {
    memorySession.accessToken = accessToken;
    try {
        sessionStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
    } catch {
        // ignore storage failures (e.g. disabled storage)
    }
    notifyTokenListeners();
};

export const clearSession = () => {
    memorySession = {};
    try {
        sessionStorage.removeItem(ACCESS_TOKEN_KEY);
    } catch {
        // ignore storage failures
    }
    notifyTokenListeners();
};

export const setSessionFromLogin = (data: unknown) => {
    if (!data || typeof data !== 'object') return;
    const payload = data as { access_token?: string };

    if (!payload.access_token) {
        return;
    }

    setAccessToken(payload.access_token);
};

export const setSessionFromRefresh = (data: unknown) => {
    if (!data || typeof data !== 'object') return;
    const payload = data as { access_token?: string };

    if (payload.access_token) {
        setAccessToken(payload.access_token);
    }
};

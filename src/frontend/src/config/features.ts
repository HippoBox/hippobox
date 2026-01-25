const toBoolean = (value: string | undefined, fallback: boolean) => {
    if (value === undefined) return fallback;
    const normalized = value.trim().toLowerCase();
    if (!normalized) return fallback;
    return normalized === 'true' || normalized === '1' || normalized === 'yes';
};

export const DEFAULT_EMAIL_ENABLED = toBoolean(import.meta.env.VITE_EMAIL_ENABLED, true);

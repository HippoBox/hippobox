import type { ReactNode } from 'react';

type ErrorMessageProps = {
    message?: ReactNode;
    className?: string;
    tone?: 'error' | 'warning' | 'info' | 'success';
    icon?: ReactNode;
    role?: 'alert' | 'status';
    ariaLive?: 'polite' | 'assertive' | 'off';
};

const toneClasses = {
    error: 'border-rose-500/20 bg-rose-500/10 text-rose-500',
    warning: 'border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300',
    info: 'border-sky-500/30 bg-sky-500/10 text-sky-700 dark:text-sky-300',
    success: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-300',
};

export function ErrorMessage({
    message,
    className,
    tone = 'error',
    icon,
    role,
    ariaLive,
}: ErrorMessageProps) {
    if (!message) return null;
    const hasIcon = Boolean(icon);
    return (
        <p
            role={role}
            aria-live={ariaLive}
            className={[
                'rounded-md border px-3 py-2 text-xs whitespace-pre-line',
                hasIcon ? 'flex items-center gap-2' : '',
                toneClasses[tone],
                className ?? '',
            ]
                .filter(Boolean)
                .join(' ')}
        >
            {hasIcon ? <span aria-hidden="true">{icon}</span> : null}
            {message}
        </p>
    );
}

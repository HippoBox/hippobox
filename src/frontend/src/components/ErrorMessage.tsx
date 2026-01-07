import type { ReactNode } from 'react';

type ErrorMessageProps = {
    message?: ReactNode;
    className?: string;
};

export function ErrorMessage({ message, className }: ErrorMessageProps) {
    if (!message) return null;
    return (
        <p
            className={`rounded-md border whitespace-pre-line border-rose-500/20 bg-rose-500/10 px-3 py-2 text-xs text-rose-500 ${className ?? ''}`.trim()}
        >
            {message}
        </p>
    );
}
